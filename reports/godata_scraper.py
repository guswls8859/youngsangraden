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
    GODATA에서 금일 입장 총수, 주/부/후문주차장 출입구 인원을 가져온다.

    반환:
        {
            'today_total':    int,   # 입장 총수 (대시보드 표시값)
            'today_exit':     int,   # 퇴장 총수
            'main_gate_walk': int,   # 주출입구 도보
            'sub_gate_walk':  int,   # 부출입구 도보
            'rear_gate_walk': int,   # 후문주차장 도보 (2026-08 추가)
            'time_slots':     dict,  # slot_HHMM_main/sub/rear
            'nav_ok':         bool,
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
            nav_ok = True
            if not (_try_click(page, '#ext-element-707') or
                    _try_force_click(page, 'text=시간대별')):
                logger.warning('GODATA: 시간대별 탭 진입 실패 — 게이트/시간대 데이터 수집 스킵')
                nav_ok = False

            if nav_ok:
                page.wait_for_timeout(3000)
                # ── 구역비교 체크박스 (동적 ID → 텍스트 기반) ────
                if not (_try_click(page, '#O8AD_id-boxLabelEl') or
                        _try_force_click(page, 'text=구역비교') or
                        _try_force_click(page, 'label:has-text("구역비교")')):
                    logger.warning('GODATA: 구역비교 체크박스 클릭 실패 — 데이터 수집 스킵')
                    nav_ok = False

            if nav_ok:
                page.wait_for_timeout(1000)
                # ── 조회 버튼 (동적 ID → 텍스트 기반) ───────────
                if not (_try_click(page, '#O7A8_id-btnEl') or
                        _try_force_click(page, 'text=조회') or
                        _try_force_click(page, 'button:has-text("조회")')):
                    logger.warning('GODATA: 조회 버튼 클릭 실패 — 데이터 수집 스킵')
                    nav_ok = False

            # ── 구역별 데이터는 조회 후에 읽는다 (nav_ok일 때만) ─
            if nav_ok:
                page.wait_for_timeout(5000)
                body = page.inner_text('body')
            else:
                body = ''
            browser.close()

        # ── 입장 총수 파싱 (시간대별 진입 전 body에서) ──────
        m_enter = re.search(r'([\d,]+) 명\n입장\n월간', body_main)
        m_exit  = re.search(r'([\d,]+) 명\n퇴장\n월간', body_main)

        if not m_enter:
            logger.warning('GODATA: 입장 합계 파싱 실패.\n--- body_main ---\n%s\n---', body_main)
            return None

        # ── 게이트/시간대별 데이터는 nav 성공 시만 파싱 ────────
        if nav_ok:
            found = re.findall(r'[\d,]+\s*명', body)
            logger.info('[SLOT-TEST] "명" 패턴 전체(%d개): %s', len(found), found)
            # 2026-08~: 게이트 3개(주/부/후문주차장) × 입/퇴 = 6개
            # 이전:      게이트 2개(주/부)          × 입/퇴 = 4개
            # 토·일: GODATA가 주간 누적합을 앞에 추가할 수 있으므로 마지막 그룹 사용
            if len(found) >= 6:
                # [ ..., 부입, 부퇴, 주입, 주퇴, 후입, 후퇴 ]
                sub_gate  = _parse_count(found[-6])
                main_gate = _parse_count(found[-4])
                rear_gate = _parse_count(found[-2])
            elif len(found) >= 4:
                # 하위호환: [ ..., 부입, 부퇴, 주입, 주퇴 ]
                sub_gate  = _parse_count(found[-4])
                main_gate = _parse_count(found[-2])
                rear_gate = None
            else:
                logger.warning('GODATA: "명" 패턴 부족 (%d개) — 게이트 None 처리', len(found))
                sub_gate  = None
                main_gate = None
                rear_gate = None
            time_slots = _parse_time_slots(body)
        else:
            sub_gate   = None
            main_gate  = None
            rear_gate  = None
            time_slots = None  # None → DB 업데이트 스킵

        return {
            'today_total':    _parse_count(m_enter.group(1)),
            'today_exit':     _parse_count(m_exit.group(1)) if m_exit else 0,
            'main_gate_walk': main_gate,
            'sub_gate_walk':  sub_gate,
            'rear_gate_walk': rear_gate,
            'time_slots':     time_slots,
            'nav_ok':         nav_ok,
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

    # ── 항상 갱신 (대시보드에서 안정적으로 읽힘) ──
    godata_fields = {
        'godata_total':   godata_pedestrian,
        'today_total':    godata_pedestrian + car_visit,
    }

    # ── nav 성공 시에만 게이트/시간대 데이터 갱신 ──
    if data.get('nav_ok'):
        main_g = data.get('main_gate_walk')
        sub_g  = data.get('sub_gate_walk')
        rear_g = data.get('rear_gate_walk')
        if main_g is not None:
            godata_fields['main_gate_walk'] = main_g
        if sub_g is not None:
            godata_fields['sub_gate_walk']  = sub_g
        if rear_g is not None:
            godata_fields['rear_gate_walk'] = rear_g
        time_slots = data.get('time_slots') or {}
        if time_slots:
            logger.info('[SLOT-TEST] 저장할 시간대별 데이터: %s', time_slots)
            godata_fields.update(time_slots)
    else:
        logger.warning(
            'GODATA: 시간대별 페이지 진입 실패 — 게이트/시간대 필드는 기존 값 유지'
        )

    ops, created = OperationsDailyData.objects.get_or_create(
        report_date=target_date,
        defaults=godata_fields,
    )

    if not created:
        for field, value in godata_fields.items():
            setattr(ops, field, value)
        ops.save(update_fields=list(godata_fields.keys()) + ['updated_at'])

    logger.info(
        'GODATA 동기화 완료: %s 도보=%d 차량=%d 입장총수=%d 주=%s 부=%s 후문=%s nav=%s (신규=%s)',
        target_date,
        godata_pedestrian,
        car_visit,
        godata_pedestrian + car_visit,
        data.get('main_gate_walk') if data.get('nav_ok') else '미수집',
        data.get('sub_gate_walk')  if data.get('nav_ok') else '미수집',
        data.get('rear_gate_walk') if data.get('nav_ok') else '미수집',
        data.get('nav_ok'),
        created,
    )
    return True


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _parse_time_slots(body: str) -> dict:
    """
    body에서 시간대별 주/부/후문주차장 입장 인원을 파싱한다.

    GODATA body 구조 (줄 단위, 2026-08~ 6개 숫자):
        09:00 ~ 10:00
        {부출입구 입장}   ← nums[0]
        {부출입구 퇴장}   ← nums[1]  (저장 안 함)
        {주출입구 입장}   ← nums[2]
        {주출입구 퇴장}   ← nums[3]  (저장 안 함)
        {후문주차장 입장} ← nums[4]  (2026-08 추가)
        {후문주차장 퇴장} ← nums[5]  (저장 안 함)
        10:00 ~ 11:00
        ...

    반환: {'slot_0900_sub': int, 'slot_0900_main': int, 'slot_0900_rear': int, ...}
    실패 시 빈 dict.

    [테스트 모드] 파싱 과정 전체를 INFO 로그로 출력.
    """
    logger.info('[SLOT-TEST] ─── 시간대별 파싱 시작 ───')
    logger.info('[SLOT-TEST] body 길이: %d자', len(body))

    lines = [l.strip() for l in body.split('\n') if l.strip()]
    logger.info('[SLOT-TEST] 공백 제거 후 총 %d줄', len(lines))

    # ── 시간대 줄 탐색 ("09:00 ~ 10:00" 형식, 공백 허용) ──
    TIME_RE = re.compile(r'^(\d{2}):\d{2}\s*~\s*\d{2}:\d{2}$')
    NUM_RE  = re.compile(r'^[\d,]+$')

    slot_indices = [(i, TIME_RE.match(line).group(1))
                    for i, line in enumerate(lines) if TIME_RE.match(line)]
    logger.info('[SLOT-TEST] 시간대 줄 %d개: %s', len(slot_indices),
                [(h, lines[i]) for i, h in slot_indices])

    if not slot_indices:
        logger.warning('[SLOT-TEST] 시간대 패턴 없음 — body 앞 80줄:\n%s', '\n'.join(lines[:80]))
        return {}

    # ── "명" 합계줄 시작 위치 (슬롯 블록 종료 기준) ─────────
    명_start = next((i for i, l in enumerate(lines) if '명' in l), len(lines))

    results = {}
    NUM_ONLY_RE = re.compile(r'^[\d,]+$')

    for idx, (line_idx, start_h) in enumerate(slot_indices):
        next_slot = slot_indices[idx + 1][0] if idx + 1 < len(slot_indices) else 명_start
        block = lines[line_idx + 1: next_slot]  # 시간대 줄 제외, 다음 시간대 전까지

        nums = [int(l.replace(',', '')) for l in block if NUM_ONLY_RE.match(l)]
        logger.info('[SLOT-TEST] %s:00 블록=%s → 숫자=%s', start_h, block, nums)

        if len(nums) < 3:
            logger.warning('[SLOT-TEST] %s:00 숫자 부족(%d개) — 스킵', start_h, len(nums))
            continue

        # nums[0]=부입, nums[1]=부퇴, nums[2]=주입, nums[3]=주퇴, nums[4]=후입, nums[5]=후퇴
        sub_entry  = nums[0]
        main_entry = nums[2]
        rear_entry = nums[4] if len(nums) >= 5 else None
        key        = f'slot_{start_h}00'
        results[f'{key}_sub']  = sub_entry
        results[f'{key}_main'] = main_entry
        if rear_entry is not None:
            results[f'{key}_rear'] = rear_entry
        logger.info('[SLOT-TEST] %s:00 → 주=%d 부=%d 후문=%s',
                    start_h, main_entry, sub_entry,
                    rear_entry if rear_entry is not None else '없음')

    logger.info('[SLOT-TEST] ─── 최종 파싱 결과 (%d슬롯): %s ───', len(results) // 2, results)
    return results


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
