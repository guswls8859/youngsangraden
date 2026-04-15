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
NS = {'hp': HP}

BASE_HWPX = Path(__file__).parent / 'data' / 'base_report.hwpx'


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


def _sf_val(slot, key):
    """스포츠필드 슬롯 값을 문자열로 변환. 값 없으면 '-'."""
    if not slot:
        return '-'
    val = slot.get(key)
    return str(val) if val is not None else '-'


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


# ── 메인 함수 ─────────────────────────────────────────────────────────────────

def build_integrated_daily_hwpx(
    target_date, ops, sf_slots, eoulrim, jamjam, kumnare,
    info_report, info_shuttle_items=None, info_patrol_items=None, total_sales=0
):
    """일일보고 HWPX 파일의 bytes를 반환한다."""

    # 1. 데이터 정리
    today_total   = _v(ops, 'today_total')
    car_visit     = _v(ops, 'car_visit')
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

    eoulrim_s = getattr(eoulrim, 'daily_net_sales', 0) or 0
    jamjam_s  = getattr(jamjam,  'daily_net_sales', 0) or 0
    kumnare_s = getattr(kumnare, 'sales_amount',    0) or 0

    # info_report / info_shuttle_items / info_patrol_items / total_sales:
    # 현재 HWPX 양식에는 해당 섹션이 없어 사용하지 않음 (PDF용 파라미터)
    _ = (info_report, info_shuttle_items, info_patrol_items, total_sales)

    st_rows = (sf_slots or {}).get('st_rows', [])
    bb_rows = (sf_slots or {}).get('bb_rows', [])
    while len(st_rows) < 3:
        st_rows.append({'label': '', 'soccer': {}, 'tennis': {}})
    while len(bb_rows) < 2:
        bb_rows.append({'label': '', 'baseball': {}, 'total': {}})

    # 2. 기반 HWPX에서 section0.xml 읽기
    with zipfile.ZipFile(BASE_HWPX, 'r') as zin:
        sec0_bytes = zin.read('Contents/section0.xml')

    root = ET.fromstring(sec0_bytes)
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
        p0_t.text = f"입장 {today_total}명"
    # 중첩 테이블: 주출입구 / 부출입구 / 차량
    # 템플릿 구조: inner_row0=헤더(3셀), inner_row1=데이터(3셀)
    inner_vtbl = cell_visit.find('.//hp:tbl', NS)
    if inner_vtbl is not None:
        v_rows = inner_vtbl.findall('hp:tr', NS)
        if len(v_rows) >= 2:
            dc = v_rows[1].findall('hp:tc', NS)
            if len(dc) >= 3:
                _set_t(dc[0], str(_v(ops, 'main_gate_walk')))
                _set_t(dc[1], str(_v(ops, 'sub_gate_walk')))
                _set_t(dc[2], str(car_visit))

    # ── Row 4: 전일 방문현황 / 명일 기상상황 ─────────────────────────────────
    cells_r4 = rows[4].findall('hp:tc', NS)
    # cells_r4[1] = col 5 (전일 총수)
    _set_para0_t(cells_r4[1], f"입장 {yesterday}명")
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
        _set_cell_lines(cells_r7[2], fac_interior)

    # ── Row 8: 잔디마당·가로수길·전망언덕 ─────────────────────────────────────
    cells_r8 = rows[8].findall('hp:tc', NS)
    _set_cell_lines(cells_r8[1], fac_outdoor)

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
    _set_cell_lines(cells_r10[1], fac_fountain)

    # ── Row 11: 주차장 (중첩 테이블) ─────────────────────────────────────────
    cells_r11 = rows[11].findall('hp:tc', NS)
    inner_parking = cells_r11[1].find('.//hp:tbl', NS)
    if inner_parking is not None:
        park_rows = inner_parking.findall('hp:tr', NS)
        if len(park_rows) >= 2:
            dc = park_rows[1].findall('hp:tc', NS)
            if len(dc) >= 4:
                _set_t(dc[0], str(p_family))
                _set_t(dc[1], str(p_dis))
                _set_t(dc[2], str(p_preg))
                _set_t(dc[3], str(p_children))

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
    _set_cell_lines(cells_r13[1], evt_internal)

    # ── Row 14: 외부행사 ──────────────────────────────────────────────────────
    cells_r14 = rows[14].findall('hp:tc', NS)
    _set_cell_lines(cells_r14[1], evt_external)

    # ── Row 15: 특이사항 ──────────────────────────────────────────────────────
    # cell1에 '○ 세부 이용현황' 단락과 내부 테이블이 있으므로
    # 특이사항 텍스트를 그 앞에 삽입한다
    cells_r15 = rows[15].findall('hp:tc', NS)
    c15 = cells_r15[1]
    sl15 = c15.find('hp:subList', NS)
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

    # 3. section0.xml 직렬화
    xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    sec0_new = (xml_decl + ET.tostring(root, encoding='unicode')).encode('utf-8')

    # 4. 새 HWPX ZIP 조립
    out = io.BytesIO()
    with zipfile.ZipFile(BASE_HWPX, 'r') as zin:
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'Contents/section0.xml':
                    zout.writestr(item, sec0_new)
                else:
                    zout.writestr(item, zin.read(item.filename))

    out.seek(0)
    return out.read()
