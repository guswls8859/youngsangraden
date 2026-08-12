"""
용산어린이정원 일일보고 - HWPX (.hwpx) 생성 모듈

실제 .hwpx 파일을 기반으로 section0.xml의 동적 데이터만 교체한다.
"""
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ── 네임스페이스 등록 ──────────────────────────────────────────────────────────
_NS_MAP = {
    'ha':          'http://www.hancom.co.kr/hwpml/2011/app',
    'hp':          'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hp10':        'http://www.hancom.co.kr/hwpml/2016/paragraph',
    'hs':          'http://www.hancom.co.kr/hwpml/2011/section',
    'hc':          'http://www.hancom.co.kr/hwpml/2011/core',
    'hh':          'http://www.hancom.co.kr/hwpml/2011/head',
    'hhs':         'http://www.hancom.co.kr/hwpml/2011/history',
    'hm':          'http://www.hancom.co.kr/hwpml/2011/master-page',
    'hpf':         'http://www.hancom.co.kr/schema/2011/hpf',
    'dc':          'http://purl.org/dc/elements/1.1/',
    'opf':         'http://www.idpf.org/2007/opf/',
    'ooxmlchart':  'http://www.hancom.co.kr/hwpml/2016/ooxmlchart',
    'hwpunitchar': 'http://www.hancom.co.kr/hwpml/2016/HwpUnitChar',
    'epub':        'http://www.idpf.org/2007/ops',
    'config':      'urn:oasis:names:tc:opendocument:xmlns:config:1.0',
}
for _pfx, _uri in _NS_MAP.items():
    ET.register_namespace(_pfx, _uri)

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
HC = 'http://www.hancom.co.kr/hwpml/2011/core'
NS = {'hp': HP, 'hc': HC}

BASE_HWPX     = Path(__file__).parent / 'data' / 'sample4.hwpx'   # 2026-08~ 통합: 방문현황 4열 + 사진 단락 포함
SAMPLE2_HWPX  = Path(__file__).parent / 'data' / 'sample2.hwpx'   # 내부행사 표 템플릿
# sample4 원본 이미지 파일 (사용자 사진으로 대체하거나 삭제됨)
_SAMPLE4_ORIG_IMAGES = {'BinData/image1.JPEG', 'BinData/image2.JPEG'}
_SAMPLE4_ORIG_IMAGE_IDS = {'image1', 'image2'}


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

def _v(obj, attr, default=0):
    """None-safe 속성 getter."""
    if obj is None:
        return default
    val = getattr(obj, attr, default)
    return val if val is not None else default


def _fmt_sales(n):
    """매출액을 천 단위 쉼표 포맷으로 변환."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return '0'


def _fmt_num(n):
    """인원수 등 정수를 3자리마다 콤마로 변환. 0/None은 '0'."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return '0'


def _bulletize(text):
    """각 줄 앞에 '○ ' 자동 부착 (이미 '○'로 시작하면 건너뜀)."""
    if not text:
        return ''
    lines = []
    for raw in text.split('\n'):
        s = raw.strip()
        if not s:
            lines.append('')
            continue
        if s.startswith('○'):
            lines.append(s)
        else:
            lines.append(f'○ {s}')
    return '\n'.join(lines)


def _sf_val(slot, key):
    """스포츠필드 슬롯 값을 문자열로 변환. 값 없으면 '-', 숫자면 콤마 포맷."""
    if not slot:
        return '-'
    val = slot.get(key)
    if val is None:
        return '-'
    try:
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return str(val)


def _set_t(cell, text):
    """셀의 첫 번째 hp:t 텍스트를 교체 (자식 요소 제거 포함)."""
    sl = cell.find('hp:subList', NS)
    if sl is None:
        return
    p = sl.find('hp:p', NS)
    if p is None:
        return
    run = p.find('hp:run', NS)
    if run is None:
        return
    t = run.find('hp:t', NS)
    if t is None:
        t = ET.SubElement(run, f'{{{HP}}}t')
    for ch in list(t):
        t.remove(ch)
    t.text = text


def _set_para0_t(cell, text):
    """셀의 첫 번째 단락 첫 번째 hp:t 텍스트를 교체."""
    sl = cell.find('hp:subList', NS)
    if sl is None:
        return
    paras = sl.findall('hp:p', NS)
    if not paras:
        return
    t = paras[0].find('hp:run/hp:t', NS)
    if t is not None:
        for ch in list(t):
            t.remove(ch)
        t.text = text


def _set_cell_lines(cell, text):
    """셀 본문을 여러 줄 텍스트로 교체.
    기존 단락의 paraPrIDRef/charPrIDRef를 유지하고 단락을 재구성한다.
    """
    lines = text.split('\n') if text else ['']
    if not lines:
        lines = ['']

    sl = cell.find('hp:subList', NS)
    if sl is None:
        return
    existing = sl.findall('hp:p', NS)

    # 첫 단락에서 서식 ID 추출
    first_p = existing[0] if existing else None
    paraPr = first_p.get('paraPrIDRef', '0') if first_p else '0'
    first_run = first_p.find('hp:run', NS) if first_p else None
    charPr = first_run.get('charPrIDRef', '0') if first_run else '0'

    # 기존 단락 제거
    for p in existing:
        sl.remove(p)

    # 새 단락 추가
    for line in lines:
        p = ET.SubElement(sl, f'{{{HP}}}p', {
            'id': '0', 'paraPrIDRef': paraPr, 'styleIDRef': '0',
            'pageBreak': '0', 'columnBreak': '0', 'merged': '0',
        })
        run = ET.SubElement(p, f'{{{HP}}}run', {'charPrIDRef': charPr})
        t = ET.SubElement(run, f'{{{HP}}}t')
        t.text = line or None


def _find_main_table(sec_root):
    """section0 루트에서 본문 메인 테이블(17행×11열)을 찾는다."""
    p = sec_root.find('hp:p', NS)
    if p is None:
        raise ValueError("section0.xml에서 hp:p를 찾을 수 없습니다.")
    for run in p.findall('hp:run', NS):
        tbl = run.find('hp:tbl', NS)
        if tbl is not None:
            return tbl
    raise ValueError("section0.xml에서 메인 테이블을 찾을 수 없습니다.")


# ── 행사 표 템플릿 (sample2 row13 cell1의 nested 테이블) ───────────────────
def _load_event_template():
    """sample2에서 (행사명 단락, 4열 nested 테이블) 템플릿을 가져온다."""
    with zipfile.ZipFile(SAMPLE2_HWPX, 'r') as z:
        root = ET.fromstring(z.read('Contents/section0.xml'))
    main_tbl = _find_main_table(root)
    cell = main_tbl.findall('hp:tr', NS)[13].findall('hp:tc', NS)[1]
    sl = cell.find('hp:subList', NS)
    paras = sl.findall('hp:p', NS)
    # paras[0] = 행사명 단락 ("○ 늘봄 학교")
    # paras[1] = run 안에 nested tbl + tail 텍스트
    return paras[0], paras[1]


# 모듈 로드 시 1회만 파싱
try:
    _EV_NAME_TPL, _EV_BODY_TPL = _load_event_template()
except Exception:
    _EV_NAME_TPL, _EV_BODY_TPL = None, None


def _set_para_text(para, text):
    """단락의 첫 hp:t에 텍스트 설정. 없으면 만들어 넣음."""
    run = para.find('hp:run', NS)
    if run is None:
        return
    t = run.find('hp:t', NS)
    if t is None:
        t = ET.SubElement(run, f'{{{HP}}}t')
    for ch in list(t):
        t.remove(ch)
    t.text = text


def _make_event_blocks(events):
    """internal_events 리스트 → (단락, 단락, …) 리스트 반환.
    각 행사마다 이름 단락 + 표 단락 2개를 만든다."""
    from copy import deepcopy
    blocks = []
    if not events or _EV_NAME_TPL is None:
        return blocks

    def _normalize_cols(cols_raw):
        """[{header, value}] 또는 {headers, rows} 형식을 (headers, rows)로 통일."""
        if isinstance(cols_raw, dict) and 'headers' in cols_raw:
            return (
                list(cols_raw.get('headers') or []),
                [list(r) for r in (cols_raw.get('rows') or [])],
            )
        if isinstance(cols_raw, list):
            headers = [(c.get('header') or '') for c in cols_raw if isinstance(c, dict)]
            row     = [(c.get('value')  or '') for c in cols_raw if isinstance(c, dict)]
            return headers, ([row] if any(row) else [])
        return [], []

    for ev in events:
        # 1) 이름 단락
        name_para = deepcopy(_EV_NAME_TPL)
        _set_para_text(name_para, f'○ {ev.name}')
        blocks.append(name_para)

        headers, data_rows = _normalize_cols(ev.columns_json)
        if not headers:
            continue

        # 2) 표 단락 (템플릿 → 헤더 N열 + 데이터 M행 동적 생성)
        body_para = deepcopy(_EV_BODY_TPL)
        run = body_para.find('hp:run', NS)
        tbl = run.find('hp:tbl', NS) if run is not None else None
        if tbl is None:
            blocks.append(body_para)
            continue

        tr_list = tbl.findall('hp:tr', NS)
        if len(tr_list) < 2:
            blocks.append(body_para)
            continue
        header_tr, data_tr_tpl = tr_list[0], tr_list[1]
        tpl_header_cell = header_tr.findall('hp:tc', NS)[0]
        tpl_data_cell   = data_tr_tpl.findall('hp:tc', NS)[0]

        # 기존 데이터 행들(2번째 이후) + 헤더/첫데이터 행의 셀 모두 제거
        for tr in tr_list[2:]:
            tbl.remove(tr)
        for tc in header_tr.findall('hp:tc', NS):
            header_tr.remove(tc)
        for tc in data_tr_tpl.findall('hp:tc', NS):
            data_tr_tpl.remove(tc)

        N       = len(headers)
        sz_el   = tbl.find('hp:sz', NS)
        total_w = int(sz_el.get('width')) if sz_el is not None else 36056
        cell_w  = total_w // N

        def _make_cell(template_cell, row_addr, col_addr, text, width):
            new_tc = deepcopy(template_cell)
            ca = new_tc.find('hp:cellAddr', NS)
            if ca is not None:
                ca.set('colAddr', str(col_addr))
                ca.set('rowAddr', str(row_addr))
            cs = new_tc.find('hp:cellSz', NS)
            if cs is not None:
                cs.set('width', str(width))
            sub_p = new_tc.find('hp:subList/hp:p', NS)
            if sub_p is not None:
                _set_para_text(sub_p, text)
            return new_tc

        # 헤더 행 채우기
        for i, h in enumerate(headers):
            header_tr.append(_make_cell(tpl_header_cell, 0, i, str(h or '').strip(), cell_w))

        # 데이터 행: 최소 1개 (빈 행이라도)
        rows_to_render = data_rows if data_rows else [[''] * N]

        # 첫 데이터 행 → data_tr_tpl에 채움
        first_row = rows_to_render[0]
        for i in range(N):
            v = first_row[i] if i < len(first_row) else ''
            data_tr_tpl.append(_make_cell(tpl_data_cell, 1, i, str(v).strip(), cell_w))

        # 추가 데이터 행 → data_tr_tpl 복사해서 tbl에 append
        for r_idx, row in enumerate(rows_to_render[1:], start=2):
            new_tr = deepcopy(data_tr_tpl)
            new_cells = new_tr.findall('hp:tc', NS)
            for j, cell in enumerate(new_cells):
                v = row[j] if j < len(row) else ''
                sub_p = cell.find('hp:subList/hp:p', NS)
                if sub_p is not None:
                    _set_para_text(sub_p, str(v).strip())
                ca = cell.find('hp:cellAddr', NS)
                if ca is not None:
                    ca.set('rowAddr', str(r_idx))
            tbl.append(new_tr)

        # colCnt / rowCnt 갱신
        tbl.set('colCnt', str(N))
        tbl.set('rowCnt', str(1 + len(rows_to_render)))

        blocks.append(body_para)

    return blocks


# ── 메인 함수 ─────────────────────────────────────────────────────────────────

def build_integrated_daily_hwpx(
    target_date, ops, sf_slots, eoulrim, jamjam, kumnare,
    info_report, info_shuttle_items=None, info_patrol_items=None, total_sales=0,
    internal_events=None, external_events=None, work_photos=None,
):
    """일일보고 HWPX 파일의 bytes를 반환한다.

    internal_events : list[InternalEvent] — DB의 내부행사 (없으면 ops.internal_events 자동 조회)
    external_events : list[ExternalEvent] — DB의 외부행사 (없으면 ops.external_events 자동 조회)
    work_photos     : list[FacilityWorkPhoto] — 작업사진 (없으면 ops.work_photos 자동 조회)
    """
    # 0. 관련 객체 조회 (명시적 인자 없으면 ops에서 가져옴)
    if internal_events is None:
        try:
            internal_events = list(ops.internal_events.all().order_by('order')) if hasattr(ops, 'internal_events') else []
        except Exception:
            internal_events = []
    if external_events is None:
        try:
            external_events = list(ops.external_events.all().order_by('order')) if hasattr(ops, 'external_events') else []
        except Exception:
            external_events = []
    if work_photos is None:
        try:
            work_photos = list(ops.work_photos.all().order_by('order')) if hasattr(ops, 'work_photos') else []
        except Exception:
            work_photos = []

    # 카테고리별 분리 (interior/outdoor/fountain)
    photos_by_cat = {'interior': [], 'outdoor': [], 'fountain': []}
    for wp in work_photos:
        cat = getattr(wp, 'category', 'interior') or 'interior'
        if cat in photos_by_cat:
            photos_by_cat[cat].append(wp)

    captions_by_cat = {
        'interior': _v(ops, 'facility_interior_caption', ''),
        'outdoor' : _v(ops, 'facility_outdoor_caption',  ''),
        'fountain': _v(ops, 'facility_fountain_caption', ''),
    }
    headers_by_cat = {
        'interior': '내부시설 작업사진',
        'outdoor' : '잔디마당·가로수길·전망언덕 작업사진',
        'fountain': '분수정원·잼잼카페 작업사진',
    }

    has_any_photos = any(photos_by_cat.values())

    # 1. 데이터 정리
    today_total   = _v(ops, 'today_total')
    car_visit     = _v(ops, 'car_visit')
    rear_gate     = _v(ops, 'rear_gate_walk')
    p_family      = _v(ops, 'parking_family')
    p_dis         = _v(ops, 'parking_disabled')
    p_preg        = _v(ops, 'parking_pregnant')
    p_children    = _v(ops, 'parking_children')

    yesterday     = _v(ops, 'yesterday_total')
    temp_min      = _v(ops, 'tomorrow_temp_min')
    temp_max      = _v(ops, 'tomorrow_temp_max')
    rain_pct      = _v(ops, 'tomorrow_rain_pct')

    fac_interior  = _v(ops, 'facility_interior', '')
    fac_outdoor   = _v(ops, 'facility_outdoor', '')
    fac_fountain  = _v(ops, 'facility_fountain', '')
    evt_internal  = _v(ops, 'internal_event', '')
    evt_external  = _v(ops, 'external_event', '')
    special       = _v(ops, 'special_notes', '')

    eoulrim_s = (getattr(eoulrim, 'daily_net_sales', 0) or 0) \
                 if eoulrim else _v(ops, 'manual_eoulrim_sales')
    jamjam_s  = (getattr(jamjam,  'daily_net_sales', 0) or 0) \
                 if jamjam  else _v(ops, 'manual_jamjam_sales')
    kumnare_s = (getattr(kumnare, 'sales_amount',    0) or 0) \
                 if kumnare else _v(ops, 'manual_kumnare_sales')

    # info_report / info_shuttle_items / info_patrol_items / total_sales:
    # 현재 HWPX 양식에는 해당 섹션이 없어 사용하지 않음 (PDF용 파라미터)
    _ = (info_report, info_shuttle_items, info_patrol_items, total_sales)

    st_rows = (sf_slots or {}).get('st_rows', [])
    bb_rows = (sf_slots or {}).get('bb_rows', [])
    while len(st_rows) < 3:
        st_rows.append({'label': '', 'soccer': {}, 'tennis': {}})
    while len(bb_rows) < 2:
        bb_rows.append({'label': '', 'baseball': {}, 'total': {}})

    # 2. 기반 HWPX: sample4 (통합판 — 방문현황 4열 + 사진 단락 포함)
    src_path = BASE_HWPX  # sample4
    with zipfile.ZipFile(src_path, 'r') as zin:
        sec0_bytes = zin.read('Contents/section0.xml')

    root = ET.fromstring(sec0_bytes)

    # sample4는 p0(메인표) + p1(사진단락) 구조. 사진 단락은 항상 root에서 제거,
    # 사진이 있으면 template으로 사용해서 카테고리별로 새로 append.
    from copy import deepcopy
    photo_template = None
    top_paras = root.findall('hp:p', NS)
    if len(top_paras) >= 2:
        photo_template = deepcopy(top_paras[1])
        root.remove(top_paras[1])
    tbl  = _find_main_table(root)
    rows = tbl.findall('hp:tr', NS)

    # ── Row 0: 날짜 ────────────────────────────────────────────────────────────
    date_str = f"{target_date.year}.{target_date.month:02d}.{target_date.day:02d}."
    _set_t(rows[0].findall('hp:tc', NS)[0], date_str)

    # ── Row 3: 금일 방문현황 ───────────────────────────────────────────────────
    cells_r3 = rows[3].findall('hp:tc', NS)
    cell_visit = cells_r3[1]
    visit_sl = cell_visit.find('hp:subList', NS)
    # 첫 단락: 입장 총수
    p0_t = visit_sl.findall('hp:p', NS)[0].find('hp:run/hp:t', NS)
    if p0_t is not None:
        p0_t.text = f"입장 {_fmt_num(today_total)}명"
    # 중첩 테이블 셀 배치 (템플릿 셀 개수에 따라 자동 분기)
    #   - 4열 (sample3, 2026-08~): [주출입구도보, 주출입구차량, 부출입구1도보, 부출입구2주차장도보]
    #   - 3열 (구버전 sample1):     [주출입구, 부출입구, 차량방문]
    inner_vtbl = cell_visit.find('.//hp:tbl', NS)
    if inner_vtbl is not None:
        v_rows = inner_vtbl.findall('hp:tr', NS)
        if len(v_rows) >= 2:
            dc = v_rows[1].findall('hp:tc', NS)
            if len(dc) >= 4:
                # 신규 4열
                _set_t(dc[0], _fmt_num(_v(ops, 'main_gate_walk')))  # 주출입구 도보
                _set_t(dc[1], _fmt_num(car_visit))                    # 주출입구 차량방문
                _set_t(dc[2], _fmt_num(_v(ops, 'sub_gate_walk')))     # 부출입구1 도보
                _set_t(dc[3], _fmt_num(rear_gate))                    # 부출입구2 주차장 도보
            elif len(dc) >= 3:
                # 구 3열 (하위호환)
                _set_t(dc[0], _fmt_num(_v(ops, 'main_gate_walk')))
                _set_t(dc[1], _fmt_num(_v(ops, 'sub_gate_walk')))
                _set_t(dc[2], _fmt_num(car_visit))

    # ── Row 4: 전일 방문현황 / 명일 기상상황 ─────────────────────────────────
    cells_r4 = rows[4].findall('hp:tc', NS)
    # cells_r4[1] = col 5 (전일 총수)
    _set_para0_t(cells_r4[1], f"입장 {_fmt_num(yesterday)}명")
    # cells_r4[3] = col 9 (기상)
    if len(cells_r4) >= 4:
        wx_sl = cells_r4[3].find('hp:subList', NS)
        wx_paras = wx_sl.findall('hp:p', NS) if wx_sl is not None else []
        if len(wx_paras) >= 1:
            t = wx_paras[0].find('hp:run/hp:t', NS)
            if t is not None:
                t.text = f"기온 {temp_min}°~ {temp_max}°"
        if len(wx_paras) >= 2:
            t = wx_paras[1].find('hp:run/hp:t', NS)
            if t is not None:
                t.text = f"강수확률 {rain_pct}%"

    # ── Row 7: 내부시설 점검내용 ───────────────────────────────────────────────
    cells_r7 = rows[7].findall('hp:tc', NS)
    # cells_r7[2] = col 5 (content)
    if len(cells_r7) >= 3:
        _set_cell_lines(cells_r7[2], _bulletize(fac_interior))

    # ── Row 8: 잔디마당·가로수길·전망언덕 ─────────────────────────────────────
    cells_r8 = rows[8].findall('hp:tc', NS)
    _set_cell_lines(cells_r8[1], _bulletize(fac_outdoor))

    # ── Row 9: 스포츠필드 (중첩 테이블 값만 교체) ────────────────────────────
    cells_r9 = rows[9].findall('hp:tc', NS)
    inner_stbl = cells_r9[1].find('.//hp:tbl', NS)
    if inner_stbl is not None:
        s_rows = inner_stbl.findall('hp:tr', NS)
        # 축구장·테니스장 (s_rows[2], [3], [4])
        for i, sr in enumerate(st_rows):
            if 2 + i >= len(s_rows):
                break
            #작업중임
            dc = s_rows[2 + i].findall('hp:tc', NS)
            if len(dc) < 7:
                continue
            soccer = sr.get('soccer') or {}
            tennis = sr.get('tennis') or {}
            _set_t(dc[1], _sf_val(soccer, 'cat'))
            _set_t(dc[2], _sf_val(soccer, 'reserved'))
            _set_t(dc[3], _sf_val(soccer, 'actual'))
            _set_t(dc[4], _sf_val(tennis, 'cat'))
            _set_t(dc[5], _sf_val(tennis, 'reserved'))
            _set_t(dc[6], _sf_val(tennis, 'actual'))
        # 야구장·합계 (s_rows[7], [8]) — 합계 분류는 1타임=일반, 2타임=쿼터 고정
        _TOTAL_CAT_LABELS = ['일반', '쿼터']
        for i, br in enumerate(bb_rows):
            if 7 + i >= len(s_rows):
                break
            dc = s_rows[7 + i].findall('hp:tc', NS)
            if len(dc) < 7:
                continue
            baseball = br.get('baseball') or {}
            total    = br.get('total') or {}
            _set_t(dc[1], _sf_val(baseball, 'cat'))
            _set_t(dc[2], _sf_val(baseball, 'reserved'))
            _set_t(dc[3], _sf_val(baseball, 'actual'))
            _set_t(dc[4], _TOTAL_CAT_LABELS[i])          # 고정 라벨
            _set_t(dc[5], _sf_val(total, 'reserved'))
            _set_t(dc[6], _sf_val(total, 'actual'))

    # ── Row 10: 분수정원·잼잼카페 ─────────────────────────────────────────────
    cells_r10 = rows[10].findall('hp:tc', NS)
    _set_cell_lines(cells_r10[1], _bulletize(fac_fountain))

    # ── Row 11: 주차장 (중첩 테이블) ─────────────────────────────────────────
    cells_r11 = rows[11].findall('hp:tc', NS)
    inner_parking = cells_r11[1].find('.//hp:tbl', NS)
    if inner_parking is not None:
        park_rows = inner_parking.findall('hp:tr', NS)
        if len(park_rows) >= 2:
            dc = park_rows[1].findall('hp:tc', NS)
            if len(dc) >= 4:
                _set_t(dc[0], _fmt_num(p_family))
                _set_t(dc[1], _fmt_num(p_dis))
                _set_t(dc[2], _fmt_num(p_preg))
                _set_t(dc[3], _fmt_num(p_children))

    # ── Row 12: 편익시설 매출 (중첩 테이블) ───────────────────────────────────
    cells_r12 = rows[12].findall('hp:tc', NS)
    inner_sales = cells_r12[1].find('.//hp:tbl', NS)
    if inner_sales is not None:
        sal_rows = inner_sales.findall('hp:tr', NS)
        if len(sal_rows) >= 2:
            dc = sal_rows[1].findall('hp:tc', NS)
            if len(dc) >= 3:
                _set_t(dc[0], _fmt_sales(eoulrim_s))
                _set_t(dc[1], _fmt_sales(jamjam_s))
                _set_t(dc[2], _fmt_sales(kumnare_s))

    # ── Row 13: 내부행사/프로그램 ─────────────────────────────────────────────
    cells_r13 = rows[13].findall('hp:tc', NS)
    if internal_events:
        # sample2와 동일한 구조 — 각 행사마다 (이름 단락 + 4열 표)
        cell13 = cells_r13[1]
        sl13 = cell13.find('hp:subList', NS)
        if sl13 is not None:
            # 기존 단락 제거 후 새 블록 삽입
            for p_old in sl13.findall('hp:p', NS):
                sl13.remove(p_old)
            for block in _make_event_blocks(internal_events):
                sl13.append(block)
    else:
        _set_cell_lines(cells_r13[1], evt_internal)

    # ── Row 14: 외부행사 ──────────────────────────────────────────────────────
    cells_r14 = rows[14].findall('hp:tc', NS)
    if external_events:
        cell14 = cells_r14[1]
        sl14 = cell14.find('hp:subList', NS)
        if sl14 is not None:
            for p_old in sl14.findall('hp:p', NS):
                sl14.remove(p_old)
            for block in _make_event_blocks(external_events):
                sl14.append(block)
    else:
        _set_cell_lines(cells_r14[1], evt_external)

    # ── Row 15: 특이사항 + 세부 이용현황 (셔틀/대여/스탬프) ─────────────────────
    # cell1에 '○ 세부 이용현황' 단락과 내부 테이블이 있으므로
    # 특이사항 텍스트를 그 앞에 삽입한다
    cells_r15 = rows[15].findall('hp:tc', NS)
    c15 = cells_r15[1]
    sl15 = c15.find('hp:subList', NS)

    # 세부 이용현황 값 결정 (보고서 우선, 없으면 수기값)
    shuttle_n = (info_report.shuttle_total if info_report else None) or _v(ops, 'manual_shuttle_total')
    rental_n  = (kumnare.rental_total_users if kumnare else None) or _v(ops, 'manual_rental_total')
    stamp_n   = (kumnare.stamp_issued       if kumnare else None) or _v(ops, 'manual_stamp_total')

    # 세부 이용현황 내부 표 값 채우기 (행 1 = 데이터 행)
    if sl15 is not None:
        for para_in_15 in sl15.findall('hp:p', NS):
            inner_tbl = para_in_15.find('hp:run/hp:tbl', NS)
            if inner_tbl is None:
                continue
            inner_rows = inner_tbl.findall('hp:tr', NS)
            if len(inner_rows) < 2:
                continue
            data_cells = inner_rows[1].findall('hp:tc', NS)
            if len(data_cells) >= 3:
                _set_t(data_cells[0], f'{_fmt_num(shuttle_n)}명')
                _set_t(data_cells[1], f'{_fmt_num(rental_n)}명')
                _set_t(data_cells[2], f'{_fmt_num(stamp_n)}명')
            break  # 첫 번째 nested table만 처리
    if sl15 is not None and special:
        existing15 = sl15.findall('hp:p', NS)
        first_p15 = existing15[0] if existing15 else None
        paraPr15 = first_p15.get('paraPrIDRef', '0') if first_p15 else '0'
        first_run15 = first_p15.find('hp:run', NS) if first_p15 else None
        charPr15 = first_run15.get('charPrIDRef', '0') if first_run15 else '0'
        children15 = list(sl15)
        insert_idx = children15.index(existing15[0]) if existing15 else len(children15)
        for i, line in enumerate(special.split('\n')):
            new_p = ET.Element(f'{{{HP}}}p', {
                'id': '0', 'paraPrIDRef': paraPr15, 'styleIDRef': '0',
                'pageBreak': '0', 'columnBreak': '0', 'merged': '0',
            })
            new_run = ET.SubElement(new_p, f'{{{HP}}}run', {'charPrIDRef': charPr15})
            new_t = ET.SubElement(new_run, f'{{{HP}}}t')
            new_t.text = line or None
            sl15.insert(insert_idx + i, new_p)

    # ── 작업사진: 카테고리별 photo 단락 3개 (있는 것만) ──────
    photo_assets   = {}
    manifest_items = []
    unused_ids     = set()
    if has_any_photos and photo_template is not None:
        photo_assets, manifest_items, unused_ids = _attach_work_photos_multi(
            root, photos_by_cat, captions_by_cat, headers_by_cat,
            photo_template=photo_template,
        )

    # 3. section0.xml 직렬화
    xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    sec0_new = (xml_decl + ET.tostring(root, encoding='unicode')).encode('utf-8')

    # 4. 새 HWPX ZIP 조립 — base=sample4, 사용자 사진으로 원본 이미지 대체
    #  - sample4 원본 image1.JPEG/image2.JPEG 파일 항상 제거
    #  - manifest에서 image1/image2 opf:item 제거 후 새 파일명(.jpeg)으로 재등록
    out = io.BytesIO()
    with zipfile.ZipFile(src_path, 'r') as zin:
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in _SAMPLE4_ORIG_IMAGES:
                    continue  # sample4 원본 이미지 항상 스킵
                if item.filename == 'Contents/section0.xml':
                    zout.writestr(item, sec0_new)
                elif item.filename == 'Contents/content.hpf':
                    hpf_xml = zin.read(item.filename).decode('utf-8')
                    # 원본 이미지 manifest 항목 항상 제거
                    hpf_xml = _strip_manifest_items(hpf_xml, _SAMPLE4_ORIG_IMAGE_IDS)
                    # 신규 삽입된 image들 manifest 항목 추가
                    extra_items = [
                        {'id': fname.split('/')[-1].rsplit('.', 1)[0],
                         'href': fname,
                         'media_type': 'image/jpeg'}
                        for fname in photo_assets
                    ]
                    if extra_items:
                        hpf_xml = _inject_manifest_items(hpf_xml, extra_items)
                    if manifest_items:
                        hpf_xml = _inject_manifest_items(hpf_xml, manifest_items)
                    zout.writestr(item, hpf_xml.encode('utf-8'))
                else:
                    zout.writestr(item, zin.read(item.filename))
            # 새 사진 파일 추가 (image1.jpeg, image2.jpeg, ...)
            for fname, data in photo_assets.items():
                zout.writestr(fname, data)

    out.seek(0)
    return out.read()


def _strip_manifest_items(hpf_xml, unused_ids):
    """content.hpf의 manifest에서 미사용 image id들에 해당하는 opf:item을 제거."""
    import re
    for img_id in unused_ids:
        pattern = rf'<opf:item\s+id="{re.escape(img_id)}"[^>]*?/>'
        hpf_xml = re.sub(pattern, '', hpf_xml)
    return hpf_xml


# ── 작업사진 처리 헬퍼 ─────────────────────────────────────────────────────────

def _attach_work_photos_multi(root, photos_by_cat, captions_by_cat, headers_by_cat,
                              photo_template=None):
    """카테고리별로 작업사진 단락을 root에 부착.

    photo_template : 외부에서 주입한 사진 단락 템플릿 (sample1에서 뽑아 온 것).
                     None이면 root의 두 번째 paragraph를 템플릿으로 사용 (하위호환).
    사진 ID는 글로벌 카운터(image1, image2, ...).

    Returns:
        photo_assets   : {'BinData/imageN.jpeg': bytes, ...} — 사용자 사진
        manifest_items : []  (manifest 추가는 빌더에서 처리)
        unused_ids     : 미사용 템플릿 image ID (예: 총 2장만 쓰면 image3, image4가 미사용)
    """
    from copy import deepcopy

    photo_assets = {}

    if photo_template is None:
        paras = root.findall('hp:p', NS)
        if len(paras) < 2:
            return photo_assets, [], set()
        template_source = paras[1]
        template_copy = deepcopy(template_source)
        root.remove(template_source)
    else:
        template_copy = deepcopy(photo_template)

    image_idx_counter = [1]   # 글로벌 image 카운터

    for cat in ('interior', 'outdoor', 'fountain'):
        photos = photos_by_cat.get(cat) or []
        if not photos:
            continue
        para = deepcopy(template_copy)
        _fill_photo_paragraph(
            para, photos, captions_by_cat.get(cat, ''), headers_by_cat.get(cat, '작업사진'),
            photo_assets, image_idx_counter,
        )
        root.append(para)

    # 템플릿(sample1)이 가진 image1~image4 중에서 글로벌 카운터가 도달 못 한 ID는 미사용
    total_used = image_idx_counter[0] - 1
    unused_ids = {f'image{i}' for i in range(total_used + 1, 5)}

    return photo_assets, [], unused_ids


def _fill_photo_paragraph(para, photos, caption, header_text,
                          photo_assets, image_idx_counter):
    """한 카테고리의 photo 단락을 채운다. para는 sample1 템플릿 deepcopy."""
    photo_tbl = para.find('hp:run/hp:tbl', NS)
    if photo_tbl is None:
        return

    rows = photo_tbl.findall('hp:tr', NS)
    if len(rows) < 3:
        return

    header_row  = rows[0]
    img_rows    = rows[1:-1]
    caption_row = rows[-1]

    # 헤더 텍스트
    header_p = header_row.findall('hp:tc', NS)[0].find('hp:subList/hp:p', NS)
    if header_p is not None:
        _set_para_text(header_p, header_text)

    # 사진 셀 수집
    pic_cells = []
    for r in img_rows:
        for tc in r.findall('hp:tc', NS):
            pic = tc.find('.//hp:pic', NS)
            if pic is not None:
                pic_cells.append((tc, pic))

    used = 0
    for idx, wp in enumerate(photos):
        if idx >= len(pic_cells):
            break
        tc, pic = pic_cells[idx]
        img_elem = pic.find('hc:img', NS)
        if img_elem is None:
            continue
        try:
            wp.image.open('rb')
            data = wp.image.read()
            wp.image.close()
        except Exception:
            continue
        new_id = f'image{image_idx_counter[0]}'
        image_idx_counter[0] += 1
        img_elem.set('binaryItemIDRef', new_id)
        photo_assets[f'BinData/{new_id}.jpeg'] = data
        used += 1

    # 빈 이미지 행 통째로 삭제 + 마지막 행에 사진이 1장만 있으면 전체 폭으로 확장
    PER_ROW = 2
    needed_rows = (used + PER_ROW - 1) // PER_ROW
    for r in img_rows[needed_rows:]:
        photo_tbl.remove(r)
    remaining = img_rows[:needed_rows]
    cells_in_last = used - (needed_rows - 1) * PER_ROW if needed_rows else 0
    if remaining and cells_in_last < PER_ROW and cells_in_last > 0:
        last_row = remaining[-1]
        last_cells = last_row.findall('hp:tc', NS)
        # 사용 안 하는 셀들의 너비 합산
        extra_width = 0
        for c in last_cells[cells_in_last:]:
            cs = c.find('hp:cellSz', NS)
            if cs is not None:
                try:
                    extra_width += int(cs.get('width') or 0)
                except (TypeError, ValueError):
                    pass
            last_row.remove(c)
        # 남은 마지막 셀 너비/colSpan 확장
        kept_cell = last_cells[cells_in_last - 1]
        cs = kept_cell.find('hp:cellSz', NS)
        if cs is not None and extra_width:
            try:
                cs.set('width', str(int(cs.get('width') or 0) + extra_width))
            except (TypeError, ValueError):
                pass
        sp = kept_cell.find('hp:cellSpan', NS)
        if sp is not None:
            try:
                sp.set('colSpan', str(int(sp.get('colSpan') or 1) + (PER_ROW - cells_in_last)))
            except (TypeError, ValueError):
                pass
    photo_tbl.set('rowCnt', str(1 + needed_rows + 1))

    # 캡션
    cap_cell = caption_row.findall('hp:tc', NS)[0]
    cap_p = cap_cell.find('hp:subList/hp:p', NS)
    if cap_p is not None:
        _set_para_text(cap_p, caption or '')


def _attach_work_photos(root, work_photos, caption):
    """sample1을 base로 사용 중일 때 photo 단락의 이미지/캡션을 사용자 데이터로 교체.

    root            : section0의 ET 루트 (sample1 기반 — 이미 photo 단락 포함)
    work_photos     : Django FacilityWorkPhoto 인스턴스 리스트
    caption         : 캡션 텍스트

    Returns:
        photo_assets   : {'BinData/imageN.ext': bytes, ...}  사용자 사진 (덮어쓰기)
        manifest_items : []
        unused_ids     : set of image IDs to EXCLUDE from output (e.g. {'image3', 'image4'})
    """
    photo_assets = {}
    manifest_items = []
    unused_ids = set()

    paras = root.findall('hp:p', NS)
    if len(paras) < 2:
        return photo_assets, manifest_items, unused_ids
    photo_para = paras[1]
    photo_tbl = photo_para.find('hp:run/hp:tbl', NS)
    if photo_tbl is None:
        return photo_assets, manifest_items, unused_ids

    rows = photo_tbl.findall('hp:tr', NS)
    if len(rows) < 3:
        return photo_assets, manifest_items, unused_ids

    img_rows    = rows[1:-1]
    caption_row = rows[-1]

    # 사진 셀 수집
    pic_cells = []
    for r in img_rows:
        for tc in r.findall('hp:tc', NS):
            pic = tc.find('.//hp:pic', NS)
            if pic is not None:
                pic_cells.append((tc, pic))

    used = 0
    for idx, wp in enumerate(work_photos):
        if idx >= len(pic_cells):
            break
        tc, pic = pic_cells[idx]
        img_elem = pic.find('hc:img', NS)
        if img_elem is None:
            continue
        # 사용자 사진 바이트 읽기
        try:
            f = wp.image.open('rb')
            data = wp.image.read()
            wp.image.close()
        except Exception:
            continue
        # sample1의 BinData/imageN.jpeg를 동일 이름으로 덮어쓰기
        img_id = img_elem.get('binaryItemIDRef')  # 'image1'~'image4'
        if not img_id:
            continue
        # 원본 sample1과 동일하게 .jpeg 확장자 사용 (HWPX는 binItemIDRef로만 매칭)
        fname = f'BinData/{img_id}.jpeg'
        photo_assets[fname] = data
        used += 1

    # 남는 셀의 미사용 image ID 수집 (BinData/manifest 정리용)
    for idx in range(used, len(pic_cells)):
        tc, pic = pic_cells[idx]
        img_elem = pic.find('hc:img', NS)
        if img_elem is not None:
            unused_id = img_elem.get('binaryItemIDRef')
            if unused_id:
                unused_ids.add(unused_id)

    # ── 빈 이미지 행 통째로 삭제 (한 행=2셀 단위) ────────────
    # 사용 셀 수에 따라 필요한 행 수만 남기고 제거
    PER_ROW = 2
    needed_rows = (used + PER_ROW - 1) // PER_ROW  # ceil(used/2)
    remove_rows = img_rows[needed_rows:]
    for r in remove_rows:
        photo_tbl.remove(r)

    # 남긴 마지막 행에서 사용 안 한 셀(예: 사진 1장만 → 두번째 셀)도 제거
    remaining_img_rows = img_rows[:needed_rows]
    cells_used_in_last_row = used - (needed_rows - 1) * PER_ROW if needed_rows else 0
    if remaining_img_rows and cells_used_in_last_row < PER_ROW:
        last_row = remaining_img_rows[-1]
        last_row_cells = last_row.findall('hp:tc', NS)
        # 사용한 셀만 남기고 나머지 제거
        for c in last_row_cells[cells_used_in_last_row:]:
            last_row.remove(c)

    # 테이블의 rowCnt 갱신
    new_row_count = 1 + needed_rows + 1  # 헤더 + 이미지 행 + 캡션
    photo_tbl.set('rowCnt', str(new_row_count))

    # 캡션 갱신
    cap_cell = caption_row.findall('hp:tc', NS)[0]
    cap_p = cap_cell.find('hp:subList/hp:p', NS)
    if cap_p is not None:
        _set_para_text(cap_p, caption or '')

    return photo_assets, manifest_items, unused_ids


def _inject_manifest_items(hpf_xml, items):
    """content.hpf의 <opf:manifest> 안에 image 아이템들을 삽입."""
    insert_block = ''
    for it in items:
        insert_block += (
            f'<opf:item id="{it["id"]}" href="{it["href"]}" '
            f'media-type="{it["media_type"]}" isEmbeded="1"/>'
        )
    # </opf:manifest> 앞에 삽입
    return hpf_xml.replace('</opf:manifest>', insert_block + '</opf:manifest>')
