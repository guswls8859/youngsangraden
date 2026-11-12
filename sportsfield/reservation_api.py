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
# 정의서 기준값: limit 기본 50 (최대 API_MAX_LIMIT), 기간은 API_MAX_DAYS 이내.
# 두 값 모두 아직 미확정 → 정의서 예시(9일·50건) 이내인 7일·50건으로 호출한다.
# 확정되면 아래 값만 조정. (범위를 넘기면 서버가 잘라서 응답할 수 있으므로 임의로 키우지 말 것)
PAGE_LIMIT = 50
CHUNK_DAYS = 7
MAX_WORKERS = 6


# API 예약번호(no)는 예전 관리자페이지 크롤링 rvNo(18465~)와 다른 번호 체계 (2026-11 신규 예약시스템).
# 번호가 겹쳐 예전 예약을 덮어쓰지 않도록 Reservation.rv_no = API_RV_NO_OFFSET + no 로 저장한다.
API_RV_NO_OFFSET = 1_000_000_000


def api_rv_no(no):
    return API_RV_NO_OFFSET + int(no)


def is_test_program(program_name):
    """예약시스템 측 테스트 데이터 (예: '축구장 (할인 테스트 중입니다. 절대 지우지 말아주세요.)')"""
    return '테스트' in (program_name or '')


class ReservationAPIError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


# ── 코드 매핑 ────────────────────────────────────────────────────────────────
# reserv_status 한글값 → Reservation.status
STATUS_MAP = {
    '예약확정': 'confirmed',
    '예약완료': 'confirmed',
    '승인대기': 'pending',
    '미선정':   'cancelled',
    '예약취소': 'cancelled',
    '':         'pending',   # 상태 빈 값 (대부분 reg_date 2026-10-20 일괄 등록분) — 확인 전까지 보고서 제외
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
        'status':             STATUS_MAP.get(rv_status.strip(), 'cancelled'),
        'rv_status':          rv_status,
        'category':           CATEGORY_MAP.get(row.get('gubun') or '', 'normal'),
        'program_name':       row.get('program_name') or '',
        'pay_status':         row.get('pay_status') or '',
        'total_users':        row.get('total_people'),
        'reservation_number': row.get('reserve_code') or str(row.get('no') or ''),
        'applied_at':         applied_at,
        # noshow_status: 'O' 이면 노쇼
        '_api_noshow':        (row.get('noshow_status') or '').strip().upper() == 'O',
    }


# ── HTTP ─────────────────────────────────────────────────────────────────────
def _get_page(session, start_date, end_date, page, limit):
    key = getattr(settings, 'RESERVATION_API_KEY', '').strip()
    if not key:
        raise ReservationAPIError('RESERVATION_API_KEY 환경변수가 설정되지 않았습니다.')
    resp = session.get(
        API_URL,
        params={
            'location': 'children', 'kind': 'sports',
            'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(),
            'page': page, 'limit': limit,
        },
        headers={'X-API-KEY': key, 'Accept': 'application/json'},
        timeout=(5, 15),   # 정의서 예제: CONNECTTIMEOUT 5 / TIMEOUT 15
        allow_redirects=False,
    )
    try:
        data = resp.json()
    except ValueError:
        raise ReservationAPIError(
            f'API 응답 JSON 파싱 실패 (HTTP {resp.status_code}): {resp.text[:200]}', resp.status_code)
    if resp.status_code == 403:
        raise ReservationAPIError(
            f'{data.get("message", "IP 차단")} — 허용 IP({ALLOWED_IP})인 서버에서만 호출할 수 있습니다.', 403)
    if resp.status_code != 200 or not data.get('success'):
        raise ReservationAPIError(
            f'API 오류 (HTTP {resp.status_code}): {data.get("message", "")}', resp.status_code)
    return data


def _chunks(start_date, end_date, days):
    cur = start_date
    while cur <= end_date:
        end = min(cur + dt.timedelta(days=days - 1), end_date)
        yield cur, end
        cur = end + dt.timedelta(days=1)


def fetch_rows(start_date, end_date):
    """기간 내 예약 전체를 가져온다. 반환: (rows, 호출 수, 경고 list)

    7일 구간별 1페이지를 병렬로 받은 뒤, pagination.total_page 까지 나머지 페이지도 병렬로 받는다.
    구간별로 받은 건수가 pagination.total 과 다르면 경고 (서버가 범위를 잘라 응답한 경우 감지).
    """
    from concurrent.futures import ThreadPoolExecutor
    chunks = list(_chunks(start_date, end_date, CHUNK_DAYS))
    by_chunk = {c: [] for c in chunks}
    totals = {}
    with requests.Session() as session:
        adapter = requests.adapters.HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
        session.mount('https://', adapter)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            firsts = list(ex.map(lambda c: _get_page(session, c[0], c[1], 1, PAGE_LIMIT), chunks))
            rest = []
            for c, data in zip(chunks, firsts):
                by_chunk[c].extend(data.get('data') or [])
                pg = data.get('pagination') or {}
                totals[c] = int(pg.get('total') or 0)
                rest += [(c, p) for p in range(2, int(pg.get('total_page') or 0) + 1)]
            pages = list(ex.map(lambda t: _get_page(session, t[0][0], t[0][1], t[1], PAGE_LIMIT), rest))
            for (c, _), data in zip(rest, pages):
                by_chunk[c].extend(data.get('data') or [])

    warnings = [
        f'{c[0]}~{c[1]}: 받은 {len(by_chunk[c])}건 / 전체 {totals[c]}건'
        for c in chunks if len(by_chunk[c]) != totals[c]
    ]
    if warnings:
        logger.warning('[예약API] 건수 불일치: %s', warnings)
    # 페이지 경계 중복 제거 (no 기준)
    uniq = {}
    for c in chunks:
        for row in by_chunk[c]:
            uniq[row.get('no')] = row
    return list(uniq.values()), len(chunks) + len(rest), warnings


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

    - rv_no = API_RV_NO_OFFSET + API no (upsert 기준, 예전 크롤링 번호와 분리)
    - 예약시스템 테스트 데이터(프로그램명에 '테스트')는 저장하지 않음
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

    import time
    from django.utils import timezone

    t0 = time.time()
    rows, n_requests, fetch_warnings = fetch_rows(start_date, end_date)
    t_fetch = time.time() - t0

    unmapped = Counter()
    errors = []
    parsed = {}
    test_skipped = 0
    for row in rows:
        if is_test_program(row.get('program_name')):
            test_skipped += 1
            continue
        try:
            defaults = row_to_defaults(row)
        except (KeyError, ValueError, TypeError) as e:
            errors.append(f'no={row.get("no")}: {e}')
            continue
        if defaults is None:
            unmapped[row.get('program_name') or '(빈 값)'] += 1
            continue
        parsed[api_rv_no(row['no'])] = defaults

    # 일괄 저장: 기존 행은 bulk_update, 신규는 bulk_create
    now = timezone.now()
    fields = [k for k in next(iter(parsed.values()), {}) if k != '_api_noshow']
    existing = Reservation.objects.in_bulk(list(parsed), field_name='rv_no')
    to_create, to_update = [], []
    for rv_no, d in parsed.items():
        api_noshow = d.pop('_api_noshow')
        obj = existing.get(rv_no)
        if obj is None:
            obj = Reservation(rv_no=rv_no, **d)
            obj.is_noshow = api_noshow
            obj.scraped_at = now
            to_create.append(obj)
        else:
            for k, v in d.items():
                setattr(obj, k, v)
            if api_noshow:
                obj.is_noshow = True      # 현장 노쇼 체크는 유지 (True로만 반영)
            obj.scraped_at = now
            to_update.append(obj)

    seen_fields = {d['field_type'] for d in parsed.values()}
    with transaction.atomic():
        if to_create:
            Reservation.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            Reservation.objects.bulk_update(
                to_update, fields + ['is_noshow', 'scraped_at'], batch_size=500)
        stale = 0
        if seen_fields:
            stale = (Reservation.objects
                     .filter(reservation_date__range=(start_date, end_date),
                             field_type__in=seen_fields)
                     .exclude(rv_no__in=list(parsed))
                     .exclude(status='cancelled')
                     .update(status='cancelled', rv_status='API 미조회'))
    created, updated = len(to_create), len(to_update)
    t_total = time.time() - t0

    result = {
        'start': start_date.isoformat(), 'end': end_date.isoformat(),
        'fetched': len(rows), 'created': created, 'updated': updated,
        'stale_cancelled': stale, 'unmapped': dict(unmapped), 'errors': errors[:20],
        'requests': n_requests, 'warnings': fetch_warnings, 'test_skipped': test_skipped,
        'fetch_sec': round(t_fetch, 1), 'total_sec': round(t_total, 1),
    }
    logger.info('[예약API] 동기화 결과: %s', result)
    return result
