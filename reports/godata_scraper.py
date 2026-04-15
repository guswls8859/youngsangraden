"""GODATA 피플카운트 스크래퍼

로그인 → 투데이 화면 → 금일 입장 총수를 추출하여 OperationsDailyData에 저장한다.
Playwright(headless chromium)를 사용한다.
"""
import logging
import re

logger = logging.getLogger(__name__)

GODATA_URL  = 'http://godata.co.kr:90/'
GODATA_ID   = 'yongsanpark'
GODATA_PW   = '1234'


def _parse_count(text: str) -> int:
    """'1,068 명' 또는 '1068' 형식에서 정수 반환. 실패 시 0."""
    m = re.search(r'[\d,]+', text)
    if m:
        return int(m.group().replace(',', ''))
    return 0


def fetch_today_entry_count() -> dict | None:
    """
    GODATA 투데이 화면에서 금일 입장 총수를 가져온다.

    반환:
        {'today_total': int, 'today_exit': int}
        실패 시 None
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error('playwright 패키지가 설치되지 않았습니다.')
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(GODATA_URL, timeout=20000)
            page.wait_for_timeout(3000)

            # 로그인
            page.fill('#O37_id-inputEl', GODATA_ID)
            page.fill('#O43_id-inputEl', GODATA_PW)
            page.click('#O4B_id-btnWrap')
            page.wait_for_timeout(5000)

            # 로딩 마스크 해제 대기
            try:
                page.wait_for_selector('.x-mask', state='hidden', timeout=15000)
            except Exception:
                pass

            # 투데이 화면은 로그인 직후 기본으로 열림
            body = page.inner_text('body')
            browser.close()

        # 입장 합계: "숫자 명\n입장\n월간" 패턴
        m_enter = re.search(r'([\d,]+) 명\n입장\n월간', body)
        m_exit  = re.search(r'([\d,]+) 명\n퇴장\n월간', body)

        if not m_enter:
            logger.warning('GODATA: 입장 합계 파싱 실패. body 앞부분: %s', body[:300])
            return None

        return {
            'today_total': _parse_count(m_enter.group(1)),
            'today_exit':  _parse_count(m_exit.group(1)) if m_exit else 0,
        }

    except Exception as exc:
        logger.exception('GODATA 스크래핑 중 오류: %s', exc)
        return None


def sync_godata_to_db(target_date=None) -> bool:
    """
    GODATA 데이터를 가져와 OperationsDailyData에 저장한다.

    target_date: datetime.date. None이면 오늘 날짜 사용.
    반환: 성공 여부 (bool)
    """
    import datetime
    from django.utils import timezone

    if target_date is None:
        target_date = timezone.localdate()

    logger.info('GODATA 동기화 시작: %s', target_date)

    data = fetch_today_entry_count()
    if data is None:
        logger.error('GODATA 동기화 실패: 데이터 수집 불가')
        return False

    from .models import OperationsDailyData

    ops, created = OperationsDailyData.objects.get_or_create(
        report_date=target_date,
        defaults={'today_total': data['today_total']},
    )

    if not created:
        # 기존 레코드가 있으면 today_total만 덮어씀
        # (직원이 직접 입력한 나머지 항목은 유지)
        ops.today_total = data['today_total']
        ops.save(update_fields=['today_total', 'updated_at'])

    logger.info(
        'GODATA 동기화 완료: %s 입장=%d명 (기존레코드=%s)',
        target_date, data['today_total'], not created,
    )
    return True
