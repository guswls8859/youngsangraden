"""GODATA 피플카운트 스크래퍼

로그인 → 대시보드 → 시간대별 → 구역비교 → 조회 → 주/부출입구 + 입장 총수 파싱
Playwright(headless chromium)를 사용한다.
"""
import logging
import re

logger = logging.getLogger(__name__)

GODATA_URL = 'http://godata.co.kr:90/'
GODATA_ID  = 'yongsanpark'
GODATA_PW  = '1234'


def _parse_count(text: str) -> int:
    """'1,068' 또는 '1068' 형식에서 정수 반환. 실패 시 0."""
    m = re.search(r'[\d,]+', text)
    return int(m.group().replace(',', '')) if m else 0


def fetch_today_entry_count() -> dict | None:
    """
    GODATA에서 금일 입장 총수, 주출입구, 부출입구 인원을 가져온다.

    반환:
        {
            'today_total':    int,  # 입장 총수
            'today_exit':     int,  # 퇴장 총수
            'main_gate_walk': int,  # 주출입구 도보
            'sub_gate_walk':  int,  # 부출입구 도보
        }
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

            # ── 접속 ─────────────────────────────────────────
            page.goto(GODATA_URL, timeout=20000)
            page.wait_for_timeout(3000)

            # ── 로그인 ────────────────────────────────────────
            page.fill('#O37_id-inputEl', GODATA_ID)
            page.fill('#O43_id-inputEl', GODATA_PW)
            page.click('#O4B_id-btnWrap')
            page.wait_for_timeout(5000)

            # ── 대시보드 ──────────────────────────────────────
            if not _try_click(page, '#ext-element-702'):
                if not _try_force_click(page, 'text=대시보드1'):
                    _force_click(page, 'text=대시보드')
            page.wait_for_timeout(3000)

            # ── 입장 총수는 시간대별 진입 전에 먼저 읽는다 ───
            body_main = page.inner_text('body')

            # ── 시간대별 탭 ───────────────────────────────────
            if not _try_click(page, '#ext-element-707'):
                _click(page, 'text=시간대별')
            page.wait_for_timeout(3000)

            # ── 구역비교 체크박스 (동적 ID → 텍스트 기반) ────
            if not _try_click(page, '#O8AD_id-boxLabelEl'):
                if not _try_force_click(page, 'text=구역비교'):
                    _force_click(page, 'label:has-text("구역비교")')
            page.wait_for_timeout(1000)

            # ── 조회 버튼 (동적 ID → 텍스트 기반) ───────────
            if not _try_click(page, '#O7A8_id-btnEl'):
                if not _try_force_click(page, 'text=조회'):
                    _force_click(page, 'button:has-text("조회")')
            page.wait_for_timeout(5000)

            # ── 구역별 데이터는 조회 후에 읽는다 ─────────────
            body = page.inner_text('body')
            browser.close()

        # ── "명" 패턴 전체 수집 → [부출입구, ?, 주출입구, ?] ──
        found = re.findall(r'[\d,]+\s*명', body)

        # ── 입장 총수 파싱 (시간대별 진입 전 body에서) ──────
        m_enter = re.search(r'([\d,]+) 명\n입장\n월간', body_main)
        m_exit  = re.search(r'([\d,]+) 명\n퇴장\n월간', body_main)

        if not m_enter:
            logger.warning('GODATA: 입장 합계 파싱 실패.\n--- body ---\n%s\n---', body)
            return None

        # ── 주/부출입구 — found 리스트 끝 4개에서 추출 ───────
        # 평일: found = [부출입구, 부퇴장, 주출입구, 주퇴장] (4개)
        # 토·일: GODATA가 주간 누적합을 앞에 추가 → 일별 합계는 항상 마지막 4개
        if len(found) >= 4:
            sub_gate  = _parse_count(found[-4])  # 부출입구
            main_gate = _parse_count(found[-2])  # 주출입구
        else:
            logger.warning('GODATA: "명" 패턴 부족 (%d개) — 주/부출입구 0으로 처리', len(found))
            sub_gate  = 0
            main_gate = 0

        return {
            'today_total':    _parse_count(m_enter.group(1)),
            'today_exit':     _parse_count(m_exit.group(1)) if m_exit else 0,
            'main_gate_walk': main_gate,
            'sub_gate_walk':  sub_gate,
        }

    except Exception as exc:
        logger.exception('GODATA 스크래핑 중 오류: %s', exc)
        return None


def sync_godata_to_db(target_date=None, data=None) -> bool:
    """
    GODATA 데이터를 OperationsDailyData에 저장한다.

    target_date : datetime.date — None이면 오늘
    data        : fetch_today_entry_count() 결과 dict — None이면 직접 수집
    반환: 성공 여부
    """
    from django.utils import timezone

    if target_date is None:
        target_date = timezone.localdate()

    logger.info('GODATA 동기화 시작: %s', target_date)

    if data is None:
        data = fetch_today_entry_count()
    if data is None:
        logger.error('GODATA 동기화 실패: 데이터 수집 불가')
        return False

    from .models import OperationsDailyData

    godata_pedestrian = data['today_total']
    car_visit = ops_existing.car_visit if (
        ops_existing := OperationsDailyData.objects.filter(report_date=target_date).first()
    ) else 0

    godata_fields = {
        'godata_total':   godata_pedestrian,
        'today_total':    godata_pedestrian + car_visit,
        'main_gate_walk': data.get('main_gate_walk', 0),
        'sub_gate_walk':  data.get('sub_gate_walk', 0),
    }

    ops, created = OperationsDailyData.objects.get_or_create(
        report_date=target_date,
        defaults=godata_fields,
    )

    if not created:
        for field, value in godata_fields.items():
            setattr(ops, field, value)
        ops.save(update_fields=list(godata_fields.keys()) + ['updated_at'])

    logger.info(
        'GODATA 동기화 완료: %s 도보=%d 차량=%d 입장총수=%d 주출입구=%d 부출입구=%d (신규=%s)',
        target_date,
        godata_pedestrian,
        car_visit,
        godata_pedestrian + car_visit,
        data.get('main_gate_walk', 0),
        data.get('sub_gate_walk', 0),
        created,
    )
    return True


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _wait_mask(page, timeout=15000):
    """x-mask 로딩 레이어가 사라질 때까지 대기."""
    try:
        page.wait_for_selector('.x-mask', state='hidden', timeout=timeout)
    except Exception:
        pass


def _click(page, selector):
    """클릭 실패 시 WARNING만 남기고 계속 진행."""
    try:
        page.click(selector, timeout=5000)
    except Exception as e:
        logger.warning('%s 클릭 실패: %s', selector, e)


def _force_click(page, selector):
    """force=True 클릭 — 오버레이에 가려진 요소에 사용. 실패 시 WARNING."""
    try:
        page.click(selector, timeout=5000, force=True)
    except Exception as e:
        logger.warning('%s 강제클릭 실패: %s', selector, e)


def _try_click(page, selector) -> bool:
    """클릭 성공 시 True, 실패 시 False 반환 (예외 없음)."""
    try:
        page.click(selector, timeout=3000)
        return True
    except Exception:
        return False


def _try_force_click(page, selector) -> bool:
    """force=True 클릭 시도 — 성공 시 True, 실패 시 False (예외 없음)."""
    try:
        page.click(selector, timeout=3000, force=True)
        return True
    except Exception:
        return False
