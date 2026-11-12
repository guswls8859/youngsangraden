"""용산공원 예약정보 조회 API 연동 (2026-11 크롤링 대체).

정의서: reports/api_file/예약정보 조회 API 연동 정의서.docx
  - GET https://yongsanparkstory.kr/_api/reservation_list.php
  - 인증: 허용 서버 IP + X-API-KEY 헤더
  - ⚠ 허용 IP는 34.64.184.142 (Cloudtype 서버 발신 IP). 로컬 PC에서 호출하면 403.
  - API 키는 환경변수 RESERVATION_API_KEY 로만 주입 (코드/저장소에 넣지 않음)
"""
import datetime as dt
import logging

import requests
from django.conf import settings

from .slots import TIME_SLOTS

logger = logging.getLogger(__name__)

API_URL = 'https://yongsanparkstory.kr/_api/reservation_list.php'
ALLOWED_IP = '34.64.184.142'
PAGE_LIMIT = 50


class ReservationAPIError(Exception):
    pass


# ── 코드 매핑 ────────────────────────────────────────────────────────────────
# reserv_status 한글값 → Reservation.status
STATUS_MAP = {
    '예약확정': 'confirmed',
    '예약완료': 'confirmed',
    '승인대기': 'pending',
    '미선정':   'cancelled',
    '예약취소': 'cancelled',
}
# gubun 한글값 → category
CATEGORY_MAP = {'일반': 'normal', '쿼터': 'quarter', '행사': 'event', '기타': 'other'}


def map_field_type(program_name):
    """program_name → FIELD_CHOICES 키. 스포츠필드가 아니면 None.

    실제 program_name 값은 서버(허용 IP)에서 확인 후 필요하면 조정.
    매핑 안 된 이름은 sync 결과의 unmapped 에 집계된다.
    """
    name = (program_name or '').replace(' ', '')
    if '야구' in name:
        return 'baseball'
    if '축구' in name:
        return 'soccer'
    if '테니스' in name:
        if '잔디' in name:
            return 'tennis_grass'
        if '하드' in name:
            return 'tennis_hard'
    return None


def _end_time(field_type, start):
    """슬롯 정의에서 종료시간을 찾고, 없으면 시작+2시간."""
    hhmm = start.strftime('%H:%M')
    for s, e, _ in TIME_SLOTS.get(field_type, []):
        if s == hhmm:
            return dt.time.fromisoformat(e)
    return (dt.datetime.combine(dt.date.today(), start) + dt.timedelta(hours=2)).time()


def _parse_time(value):
    """'10:00', '10:00:00', '10:00~12:00' 형태 모두 허용 → (start, end or None)."""
    raw = (value or '').strip()
    parts = [p.strip() for p in raw.replace('-', '~').split('~') if p.strip()]
    if not parts:
        raise ValueError(f'reserv_time 비어있음: {value!r}')
    start = dt.time.fromisoformat(parts[0][:5])
    end = dt.time.fromisoformat(parts[1][:5]) if len(parts) > 1 else None
    return start, end


def row_to_defaults(row):
    """API 예약 1건 → Reservation update_or_create defaults. 스포츠필드가 아니면 None."""
    field_type = map_field_type(row.get('program_name'))
    if not field_type:
        return None
    start, end = _parse_time(row.get('reserv_time'))
    rv_status = row.get('reserv_status') or ''
    reg_date = row.get('reg_date') or ''
    applied_at = None
    if reg_date:
        try:
            from django.utils import timezone
            applied_at = timezone.make_aware(dt.datetime.fromisoformat(reg_date[:10]))
        except ValueError:
            pass
    return {
        'field_type':         field_type,
        'reservation_date':   dt.date.fromisoformat(row['reserv_day'][:10]),
        'time_start':         start,
        'time_end':           end or _end_time(field_type, start),
        'applicant_name':     row.get('name') or '',
        'phone':              row.get('phone') or '',
        'status':             STATUS_MAP.get(rv_status, 'cancelled'),
        'rv_status':          rv_status,
        'category':           CATEGORY_MAP.get(row.get('gubun') or '', 'normal'),
        'program_name':       row.get('program_name') or '',
        'pay_status':         row.get('pay_status') or '',
        'total_users':        row.get('total_people'),
        'reservation_number': str(row.get('no') or ''),
        'applied_at':         applied_at,
        # noshow_status: 'O' 이면 노쇼
        '_api_noshow':        (row.get('noshow_status') or '').strip().upper() == 'O',
    }


# ── HTTP ─────────────────────────────────────────────────────────────────────
def _get_page(session, start_date, end_date, page):
    key = getattr(settings, 'RESERVATION_API_KEY', '')
    if not key:
        raise ReservationAPIError('RESERVATION_API_KEY 환경변수가 설정되지 않았습니다.')
    resp = session.get(
        API_URL,
        params={
            'location': 'children', 'kind': 'sports',
            'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(),
            'page': page, 'limit': PAGE_LIMIT,
        },
        headers={'X-API-KEY': key, 'Accept': 'application/json'},
        timeout=(5, 15),
        allow_redirects=False,
    )
    try:
        data = resp.json()
    except ValueError:
        raise ReservationAPIError(f'API 응답 JSON 파싱 실패 (HTTP {resp.status_code}): {resp.text[:200]}')
    if resp.status_code == 403:
        raise ReservationAPIError(
            f'{data.get("message", "IP 차단")} — 허용 IP({ALLOWED_IP})인 서버에서만 호출할 수 있습니다.')
    if resp.status_code != 200 or not data.get('success'):
        raise ReservationAPIError(f'API 오류 (HTTP {resp.status_code}): {data.get("message", "")}')
    return data


def fetch_rows(start_date, end_date, chunk_days=7):
    """기간 내 예약 전체를 가져온다. API_MAX_DAYS 제한을 고려해 chunk_days 단위로 나눠 호출."""
    rows = []
    with requests.Session() as session:
        cur = start_date
        while cur <= end_date:
            chunk_end = min(cur + dt.timedelta(days=chunk_days - 1), end_date)
            page = 1
            while True:
                data = _get_page(session, cur, chunk_end, page)
                rows.extend(data.get('data') or [])
                total_page = int((data.get('pagination') or {}).get('total_page') or 0)
                if page >= total_page:
                    break
                page += 1
            cur = chunk_end + dt.timedelta(days=1)
    return rows


# ── DB 동기화 ────────────────────────────────────────────────────────────────
def default_range(today=None):
    """기존 크롤러와 동일: 이번 달 1일 ~ 다음 달 말일."""
    today = today or dt.date.today()
    start = today.replace(day=1)
    nxt = (start + dt.timedelta(days=32)).replace(day=1)
    end = (nxt + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
    return start, end


def sync_reservations(start_date=None, end_date=None):
    """API 예약을 Reservation 테이블에 반영하고 요약 dict를 반환한다.

    - rv_no = API no (upsert 기준)
    - 노쇼: API가 'O'면 True로 반영. 현장에서 직접 체크한 노쇼는 API가 빈 값이어도 유지.
    - 사용 메모(usage_memo)는 건드리지 않음.
    - 기간 내 DB에 있으나 API에 없는 예약은 status='cancelled', rv_status='API 미조회'
      (단, 이번 응답에 한 건이라도 있었던 구장만 — 매핑 실패로 전부 지워지는 사고 방지)
    """
    from collections import Counter
    from django.db import transaction
    from .models import Reservation

    if start_date is None or end_date is None:
        start_date, end_date = default_range()

    rows = fetch_rows(start_date, end_date)

    created = updated = 0
    unmapped = Counter()
    errors = []
    seen_ids = set()
    seen_fields = set()

    with transaction.atomic():
        for row in rows:
            try:
                defaults = row_to_defaults(row)
            except (KeyError, ValueError, TypeError) as e:
                errors.append(f'no={row.get("no")}: {e}')
                continue
            if defaults is None:
                unmapped[row.get('program_name') or '(빈 값)'] += 1
                continue
            api_noshow = defaults.pop('_api_noshow')
            obj, was_created = Reservation.objects.update_or_create(
                rv_no=int(row['no']), defaults=defaults)
            if api_noshow and not obj.is_noshow:
                obj.is_noshow = True
                obj.save(update_fields=['is_noshow'])
            created += was_created
            updated += not was_created
            seen_ids.add(obj.rv_no)
            seen_fields.add(obj.field_type)

        stale = 0
        if seen_fields:
            stale = (Reservation.objects
                     .filter(reservation_date__range=(start_date, end_date),
                             field_type__in=seen_fields)
                     .exclude(rv_no__in=seen_ids)
                     .exclude(status='cancelled')
                     .update(status='cancelled', rv_status='API 미조회'))

    result = {
        'start': start_date.isoformat(), 'end': end_date.isoformat(),
        'fetched': len(rows), 'created': created, 'updated': updated,
        'stale_cancelled': stale, 'unmapped': dict(unmapped), 'errors': errors[:20],
    }
    logger.info('[예약API] 동기화 결과: %s', result)
    return result
