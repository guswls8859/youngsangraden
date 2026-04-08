import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Spacer


# ── 폰트 및 스타일 설정 ──────────────────────────────────────
_FONT_PATHS = [
    '/Library/Fonts/NanumGothic.ttf',
    '/Library/Fonts/Arial Unicode.ttf',
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
]

def _register_korean_font():
    for path in _FONT_PATHS:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', path))
                return 'Korean'
            except Exception:
                continue
    return 'Helvetica'

FONT = _register_korean_font()
FGREY = colors.HexColor('#f8f9fa')

# ── 스타일 헬퍼 ──────────────────────────────────────────────

def _s(name, **kw):
    return ParagraphStyle(name, fontName=FONT, **kw)


TITLE_S  = _s('T',   fontSize=15, leading=20, spaceAfter=3)
SUB_S    = _s('Su',  fontSize=9,  textColor=colors.grey, spaceAfter=8)
SEC_H_S  = _s('SH',  fontSize=10, leading=14, spaceAfter=3)
BODY_S   = _s('Bo',  fontSize=9,  leading=13)
SMALL_S  = _s('Sm',  fontSize=7,  textColor=colors.grey)
COVER_S  = _s('Co',  fontSize=20, leading=26, spaceAfter=6)
COVER2_S = _s('Co2', fontSize=12, textColor=colors.grey, spaceAfter=4)

BLUE   = colors.HexColor('#0d6efd')
YELLOW = colors.HexColor('#ffc107')
CYAN   = colors.HexColor('#0dcaf0')
RED    = colors.HexColor('#dc3545')
LGREY  = colors.HexColor('#dee2e6')
FGREY  = colors.HexColor('#f8f9fa')
HBLUE  = colors.HexColor('#f0f4ff')


def _progress_bar(progress, bar_color):
    pct = max(0, min(100, progress))
    filled = int(pct / 5)
    bar = '█' * filled + '░' * (20 - filled)
    return Paragraph(f'{bar} {pct}%', ParagraphStyle('pb', fontName='Helvetica', fontSize=7, textColor=bar_color))


def _task_table(tasks, bar_color, body_style):
    if not tasks:
        return Paragraph('(없음)', _s('no', fontSize=8, textColor=colors.grey))
    data = [['업무 내용', '진행률']]
    for t in tasks:
        data.append([Paragraph(t.content, body_style), _progress_bar(t.progress, bar_color)])
    tbl = Table(data, colWidths=[125*mm, 42*mm])
    tbl.setStyle(TableStyle([
        ('FONTNAME',       (0, 0), (-1, -1), FONT),
        ('FONTSIZE',       (0, 0), (-1,  0), 8),
        ('FONTSIZE',       (0, 1), (-1, -1), 9),
        ('BACKGROUND',     (0, 0), (-1,  0), HBLUE),
        ('TEXTCOLOR',      (0, 0), (-1,  0), colors.HexColor('#444')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, FGREY]),
        ('GRID',           (0, 0), (-1, -1), 0.3, LGREY),
        ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',     (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 3),
    ]))
    return tbl


# ── 단일 보고서 → story 블록 ─────────────────────────────────

def _report_story(report):
    """한 명의 보고서를 story 요소 리스트로 반환한다."""
    items = list(report.task_items.all())
    completed   = [t for t in items if t.category == 'completed']
    in_progress = [t for t in items if t.category == 'in_progress']
    tomorrow    = [t for t in items if t.category == 'tomorrow']
    author = report.author
    name = author.get_full_name() or author.username
    dept = author.department or ''
    status = '제출완료' if report.status == 'submitted' else '임시저장'

    story = []
    story.append(Paragraph('일일 업무보고서', TITLE_S))
    story.append(Paragraph(
        f'{report.report_date}  |  {name}  {dept}  |  {status}', SUB_S))
    story.append(HRFlowable(width='100%', thickness=1, color=BLUE))
    story.append(Spacer(1, 5*mm))

    for title, tasks, color in [
        ('▶ 금일 완료 업무',  completed,   BLUE),
        ('▶ 진행 중 업무',    in_progress, YELLOW),
        ('▶ 내일 예정 업무',  tomorrow,    CYAN),
    ]:
        story.append(Paragraph(title, _s(f'h{title}', fontSize=10, leading=14,
                                         spaceAfter=3, textColor=color)))
        story.append(_task_table(tasks, color, BODY_S))
        story.append(Spacer(1, 4*mm))

    story.append(Paragraph('▶ 이슈 및 특이사항',
                            _s('ih', fontSize=10, leading=14, spaceAfter=3, textColor=RED)))
    if report.issues:
        story.append(Paragraph(report.issues.replace('\n', '<br/>'), BODY_S))
    else:
        story.append(Paragraph('(없음)', _s('no2', fontSize=8, textColor=colors.grey)))

    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width='100%', thickness=0.4, color=LGREY))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph(
        f'작성: {report.created_at.strftime("%Y-%m-%d %H:%M")}  |  '
        f'수정: {report.updated_at.strftime("%Y-%m-%d %H:%M")}',
        SMALL_S))
    return story


# ── 공개 API ────────────────────────────────────────────────

def build_report_pdf(report):
    """단일 보고서 PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    doc.build(_report_story(report))
    return buf.getvalue()


def build_daily_pdf(reports, target_date):
    """일간 통합 PDF bytes. reports는 해당 날짜의 QuerySet."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    story = []
    # 표지
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('일간 업무보고서', COVER_S))
    story.append(Paragraph(str(target_date), COVER2_S))
    story.append(Paragraph(f'총 {len(list(reports))}명 제출', COVER2_S))
    story.append(PageBreak())

    reports = list(reports)  # 이미 소진됐으므로 재사용
    for i, report in enumerate(reports):
        story.extend(_report_story(report))
        if i < len(reports) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()


def _build_daily_task_story(target_date, users_tasks):
    """
    일일 업무 일지 story. info행 + 보고자 섹션 + 특이사항을 하나의 통합 테이블로 구성해
    경계선을 명확히 표시한다.
    """
    W       = 180 * mm
    LABEL_W = 25 * mm
    COL1_W  = 60 * mm          # '일일업무보고' 열
    COL2_W  = 25 * mm          # '작성일자' 열
    COL3_W  = W - LABEL_W - COL1_W - COL2_W   # 날짜 열 (70mm)
    STAMP_W = 23 * mm

    label_s = ParagraphStyle('lbl', fontName=FONT, fontSize=9, alignment=1, leading=14)
    cell_s  = ParagraphStyle('cel', fontName=FONT, fontSize=9, leading=14)

    def task_para(tasks):
        if not tasks:
            return Paragraph('', cell_s)
        lines = '<br/>'.join(f'• {t.task_name}' for t in tasks)
        return Paragraph(lines, cell_s)

    story = []

    # ── 1. 헤더 (제목 + 결재란) ──────────────────────────────
    title_s = ParagraphStyle('dt', fontName=FONT, fontSize=20, alignment=1, leading=26)
    approval_tbl = Table(
        [['담당자', '팀장', '총괄소장'], ['', '', '']],
        colWidths=[STAMP_W] * 3,
        rowHeights=[7*mm, 18*mm],
    )
    approval_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN',   (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',  (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',    (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    header_tbl = Table(
        [[Paragraph('일  일  업  무  일  지', title_s), approval_tbl]],
        colWidths=[W - STAMP_W * 3, STAMP_W * 3],
    )
    header_tbl.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    story.append(header_tbl)
    story.append(Spacer(1, 4*mm))

    # ── 2. 통합 테이블 (info + 보고자 섹션 + 특이사항) ────────
    date_str = f'{target_date.year}년 {target_date.month}월 {target_date.day}일'

    all_data    = []
    all_heights = []
    span_cmds   = []
    bg_cmds     = []

    # info 행 (4열 그대로)
    all_data.append([
        Paragraph('업무명', label_s),
        Paragraph('일일업무보고', cell_s),
        Paragraph('작성일자', label_s),
        Paragraph(date_str, cell_s),
    ])
    all_heights.append(10*mm)
    bg_cmds += [
        ('BACKGROUND', (0, 0), (0, 0), FGREY),
        ('BACKGROUND', (2, 0), (2, 0), FGREY),
    ]

    # 보고자별 3행 (col 1~3 을 SPAN)
    r = 1
    for user, done, pending in users_tasks:
        name = user.get_full_name() or user.username
    
        h_name    = 8*mm
        h_done    = max(20*mm, 5.5*mm * len(done))    if done    else 20*mm
        h_pending = max(14*mm, 5.5*mm * len(pending)) if pending else 14*mm

        for label, content, h in [
            ('보고자',     Paragraph(name, cell_s), h_name),
            ('업무사항',   task_para(done),          h_done),
            ('익일업무계획', task_para(pending),      h_pending),
        ]:
            all_data.append([Paragraph(label, label_s), content, '', ''])
            all_heights.append(h)
            span_cmds.append(('SPAN', (1, r), (3, r)))
            bg_cmds.append(('BACKGROUND', (0, r), (0, r), FGREY))
            r += 1

    # 특이사항 행 (내용 없으면 5mm 고정, 있으면 자동 확장)
    notes = [t.note for _, d, p in users_tasks for t in d + p if t.note]
    note_text = '<br/>'.join(notes) if notes else ''
    all_data.append([Paragraph('특이사항', label_s), Paragraph(note_text, cell_s), '', ''])
    all_heights.append(None if note_text else 5*mm)
    span_cmds.append(('SPAN', (1, r), (3, r)))
    bg_cmds.append(('BACKGROUND', (0, r), (0, r), FGREY))

    main_tbl = Table(
        all_data,
        colWidths=[LABEL_W, COL1_W, COL2_W, COL3_W],
        rowHeights=all_heights,
    )
    main_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0, 0), (-1, -1), FONT),
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('GRID',        (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        # 내용 셀: 상단 정렬 + 왼쪽 패딩
        ('VALIGN',      (1, 1), (1, -1), 'TOP'),
        ('TOPPADDING',  (1, 1), (1, -1), 5),
        ('LEFTPADDING', (1, 0), (1, -1), 8),
        ('LEFTPADDING', (3, 0), (3, 0),  8),
    ] + span_cmds + bg_cmds))

    story.append(main_tbl)

    # ── 3. 푸터 ──────────────────────────────────────────────
    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '용산어린이정원운영사무국',
        ParagraphStyle('ft', fontName=FONT, fontSize=10, alignment=1, textColor=colors.grey),
    ))
    return story


def build_daily_task_pdf(target_date, tasks_qs, all_users=None):
    from collections import defaultdict
    user_done    = defaultdict(list)
    user_pending = defaultdict(list)
    user_map = {}

    for t in tasks_qs:
        user_map[t.user_id] = t.user
        if t.status == 'done':
            user_done[t.user_id].append(t)
        else:
            user_pending[t.user_id].append(t)

    if all_users is not None:
        #users_tasks = [(u, user_done[u.pk], user_pending[u.pk]) for u in all_users]
        users_tasks = [(u, user_done[u.pk], user_pending[u.pk]) for u in all_users]
    else:
        users_tasks = [(user_map[uid], user_done[uid], user_pending[uid]) for uid in user_map]

    buf = io.BytesIO()
    # 여백 조정을 통해 표가 잘리지 않게 함
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    doc.build(_build_daily_task_story(target_date, users_tasks))
    return buf.getvalue()


def build_weekly_task_pdf(week_start, week_end, days, all_users=None):
    """
    주간 업무 일지 PDF bytes.
    days: {date: DailyTask QuerySet} OrderedDict/dict
    날짜별로 한 페이지씩 동일 양식으로 출력.
    all_users: 전체 직원 목록 (없으면 태스크가 있는 직원만 표시)
    """
    from collections import defaultdict
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    story = []
    first = True
    for day, tasks_qs in days.items():
        tasks = list(tasks_qs)
        if not tasks and all_users is None:
            continue
        if not first:
            story.append(PageBreak())
        first = False

        user_done    = defaultdict(list)
        user_pending = defaultdict(list)
        user_map = {}
        for t in tasks:
            user_map[t.user_id] = t.user
            if t.status == 'done':
                user_done[t.user_id].append(t)
            else:
                user_pending[t.user_id].append(t)

        if all_users is not None:
            users_tasks = [
                (user, user_done[user.pk], user_pending[user.pk])
                for user in all_users
            ]
        else:
            users_tasks = [
                (user_map[uid], user_done[uid], user_pending[uid])
                for uid in user_map
            ]
        story.extend(_build_daily_task_story(day, users_tasks))

    if not story:
        story.append(Paragraph('해당 주에 등록된 업무가 없습니다.',
                                ParagraphStyle('empty', fontName=FONT, fontSize=10)))

    doc.build(story)
    return buf.getvalue()


def build_integrated_daily_pdf(target_date, ops_data, sf_reservations, sf_entries,
                               eoulrim_report, jamjam_report, kumnare_report, info_report):
    """
    용산어린이정원 일일보고 PDF.
    - ops_data: OperationsDailyData 인스턴스 (없으면 None)
    - sf_reservations: Reservation QuerySet (해당 날짜)
    - sf_entries: SportsfieldEntry QuerySet (해당 날짜)
    - eoulrim_report / jamjam_report / kumnare_report: 해당 날짜 보고서 (없으면 None)
    - info_report: InfoReport (없으면 None)
    """
    import datetime

    W = 180 * mm   # 유효 폭 (여백 각 15mm)
    BLACK = colors.black
    DARK  = colors.HexColor('#1a1a1a')
    GREY  = colors.HexColor('#f0f0f0')
    MGREY = colors.HexColor('#d0d0d0')

    lbl_s  = ParagraphStyle('il', fontName=FONT, fontSize=8,  alignment=1, leading=11)
    val_s  = ParagraphStyle('iv', fontName=FONT, fontSize=9,  leading=12)
    val_c  = ParagraphStyle('ic', fontName=FONT, fontSize=9,  alignment=1, leading=12)
    big_s  = ParagraphStyle('ib', fontName=FONT, fontSize=11, leading=14, alignment=1)
    sm_s   = ParagraphStyle('sm', fontName=FONT, fontSize=7,  leading=10, textColor=colors.grey)
    tbl_s  = ParagraphStyle('tb', fontName=FONT, fontSize=7,  alignment=1, leading=10)

    d = ops_data  # shorthand

    def cell(txt, style=val_s, pad=2):
        return Paragraph(str(txt) if txt is not None else '', style)

    def section_row(label, content_cell, label_w=28*mm):
        """라벨 + 내용 2열 행 반환"""
        return [cell(label, lbl_s), content_cell]

    def hr():
        return HRFlowable(width='100%', thickness=0.5, color=MGREY)

    story = []

    # ── 1. 헤더 ──────────────────────────────────────────────────
    WEEKDAY_KR = ['월', '화', '수', '목', '금', '토', '일']
    wd = WEEKDAY_KR[target_date.weekday()]
    date_str = f'{target_date.year}.{target_date.month:02d}.{target_date.day:02d}. ({wd})'

    title_s  = ParagraphStyle('ht', fontName=FONT, fontSize=14, alignment=1, leading=18)
    conf_s   = ParagraphStyle('hc', fontName=FONT, fontSize=7,  alignment=1, leading=10)

    confirm_tbl = Table(
        [['확 인(L H)', '점 검(중앙)'],
         ['', '']],
        colWidths=[28*mm, 28*mm],
        rowHeights=[6*mm, 14*mm],
    )
    confirm_tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,0), 7),
        ('ALIGN',    (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',     (0,0), (-1,-1), 0.5, BLACK),
        ('BACKGROUND', (0,0), (-1,0), GREY),
    ]))

    header_tbl = Table(
        [[Paragraph(f'{date_str}   운영관리   용산어린이정원 일일보고', title_s), confirm_tbl]],
        colWidths=[W - 56*mm, 56*mm],
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN',  (0,0), (-1,-1), 'MIDDLE'),
        ('BOX',     (0,0), (-1,-1), 1.0, BLACK),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#dbe5f1')),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 2*mm))

    # ── 2. 방문현황 ───────────────────────────────────────────────
    today_t = d.today_total if d else 0
    main_w  = d.main_gate_walk if d else 0
    sub_w   = d.sub_gate_walk if d else 0
    car_v   = d.car_visit if d else 0
    yest_t  = d.yesterday_total if d else 0
    t_min   = d.tomorrow_temp_min if d else 0
    t_max   = d.tomorrow_temp_max if d else 0
    r_pct   = d.tomorrow_rain_pct if d else 0

    visit_inner = Table(
        [[cell(f'주출입구 도보방문(명)', lbl_s), cell(f'부출입구 도보방문(명)', lbl_s), cell('차량방문(명)', lbl_s)],
         [cell(f'{main_w:,}', val_c), cell(f'{sub_w:,}', val_c), cell(f'{car_v:,}', val_c)]],
        colWidths=[(W - 28*mm) / 3] * 3,
        rowHeights=[6*mm, 7*mm],
    )
    visit_inner.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN',     (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('INNERGRID', (0,0), (-1,-1), 0.3, MGREY),
        ('BACKGROUND', (0,0), (-1,0), GREY),
    ]))

    visit_tbl = Table(
        [[cell('■ 금일\n방문현황', lbl_s),
          Table([[cell(f'입장  {today_t:,}명', big_s)], [visit_inner]],
                colWidths=[W - 28*mm], rowHeights=[9*mm, None])]],
        colWidths=[28*mm, W - 28*mm],
        rowHeights=[None],
    )
    visit_tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT),
        ('BOX',      (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',(0,0), (-1,-1), 0.5, BLACK),
        ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,0), GREY),
    ]))
    story.append(visit_tbl)

    yest_weather = Table(
        [[cell('■ 전일 방문현황', lbl_s),
          cell(f'입장  {yest_t:,}명', val_c),
          cell('명일 기상상황', lbl_s),
          cell(f'기온 {t_min}°~ {t_max}°\n강수확률 {r_pct}%', val_c)]],
        colWidths=[28*mm, (W-28*mm)*0.35, 28*mm, (W-28*mm)*0.65 - 28*mm],
        rowHeights=[12*mm],
    )
    yest_weather.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.5, BLACK),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND',  (0,0), (0,0), GREY),
        ('BACKGROUND',  (2,0), (2,0), GREY),
    ]))
    story.append(yest_weather)
    story.append(Spacer(1, 1*mm))

    # ── 3. 운영관리 점검 ─────────────────────────────────────────
    LW = 28*mm
    CW = W - LW

    def ops_row(label, text, h=None):
        txt = text or ''
        return ([cell(label, lbl_s), cell(txt.replace('\n', '<br/>'), val_s)], h or (8*mm if not txt else None))

    ops_section_s = ParagraphStyle('ops', fontName=FONT, fontSize=8, alignment=1, leading=11)

    # 스포츠필드 예약 테이블
    TIME_SLOTS = {
        'soccer':       [('10:00','12:00','1타임'),('13:00','15:00','2타임'),('15:30','17:30','3타임')],
        'tennis':       [('10:00','12:00','1타임'),('13:00','15:00','2타임'),('15:30','17:30','3타임')],
        'baseball':     [('10:00','14:00','1타임'),('14:00','18:00','2타임')],
    }

    def get_sf_data(field_keys, slots):
        """field_keys: list of field_type str, slots: list of (start,end,label)"""
        rows = []
        for start_t, end_t, label in slots:
            rv_list = [r for r in sf_reservations
                       if r.field_type in field_keys
                       and r.time_start.strftime('%H:%M') == start_t
                       and r.status == 'confirmed']
            en_list = [e for e in sf_entries
                       if e.field_type in field_keys
                       and e.time_start and e.time_start.strftime('%H:%M') == start_t]
            if rv_list:
                r = rv_list[0]
                rv_cnt   = r.total_users or '-'
                actual   = (r.actual_adult_count or 0) + (r.actual_child_count or 0) or '-'
                category = '쿼터' if r.scoreboard else '일반'
            elif en_list:
                e = en_list[0]
                rv_cnt   = '-'
                actual   = (e.actual_adult_count or 0) + (e.actual_child_count or 0) or '-'
                category = e.get_category_display()
            else:
                rv_cnt, actual, category = '-', '-', '-'
            time_label = f'{label}\n({start_t}~{end_t})'
            rows.append((time_label, category, rv_cnt, actual))
        return rows

    soccer_rows   = get_sf_data(['soccer'], TIME_SLOTS['soccer'])
    tennis_rows   = get_sf_data(['tennis_grass','tennis_hard'], TIME_SLOTS['tennis'])
    baseball_rows = get_sf_data(['baseball'], TIME_SLOTS['baseball'])

    # 헤더
    sf_hdr_s = ParagraphStyle('sfh', fontName=FONT, fontSize=6.5, alignment=1, leading=9)
    def sf_cell(t, bold=False):
        fs = 7 if not bold else 7.5
        return Paragraph(str(t), ParagraphStyle('sfc', fontName=FONT, fontSize=fs, alignment=1, leading=10))

    max_soccer = max(len(soccer_rows), len(tennis_rows))
    max_rows   = max(max_soccer, len(baseball_rows))

    SF_LW  = 28*mm
    SF_COL = (W - SF_LW) / 8   # 각 필드: 분류+예약+입장 3열

    sf_data = [[
        sf_cell('구분'),
        sf_cell('축구장\n분류'), sf_cell('예약'), sf_cell('입장'),
        sf_cell('테니스장\n분류'), sf_cell('예약'), sf_cell('입장'),
        sf_cell('야구장\n분류'), sf_cell('예약'), sf_cell('입장'),
    ]]
    sf_widths = [SF_LW] + [SF_COL] * 9

    n_sf = max(len(soccer_rows), len(tennis_rows), len(baseball_rows))
    for i in range(n_sf):
        s = soccer_rows[i]   if i < len(soccer_rows)   else ('-','-','-','-')
        t = tennis_rows[i]   if i < len(tennis_rows)   else ('-','-','-','-')
        b = baseball_rows[i] if i < len(baseball_rows) else ('-','-','-','-')
        label = s[0] or t[0] or b[0]
        sf_data.append([
            sf_cell(label),
            sf_cell(s[1]), sf_cell(s[2]), sf_cell(s[3]),
            sf_cell(t[1]), sf_cell(t[2]), sf_cell(t[3]),
            sf_cell(b[1]), sf_cell(b[2]), sf_cell(b[3]),
        ])

    sf_tbl = Table(sf_data, colWidths=sf_widths, rowHeights=[8*mm] + [9*mm]*n_sf)
    sf_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',        (0,0), (-1,-1), 0.3, MGREY),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('BACKGROUND',  (0,0), (-1,0), GREY),
        ('BACKGROUND',  (0,0), (0,-1), GREY),
    ]))

    sf_note = Paragraph('○ 스포츠필드 이용 예약', ParagraphStyle('sfn', fontName=FONT, fontSize=8, leading=11))

    # 운영관리 전체 테이블
    ops_interior = (d.facility_interior if d else '') or ''
    ops_outdoor  = (d.facility_outdoor  if d else '') or ''
    ops_fountain = (d.facility_fountain if d else '') or ''

    ops_data_tbl = [
        [cell('■ 운영관리\n점검 및\n작업내용', lbl_s),
         Table([
             [cell('시설', lbl_s),
              Table([
                  [cell('내부시설\n(용산서가, 전시관 등)', lbl_s),
                   cell(ops_interior.replace('\n','<br/>') if ops_interior else '', val_s)],
                  [cell('잔디마당\n가로수길\n전망언덕', lbl_s),
                   cell(ops_outdoor.replace('\n','<br/>') if ops_outdoor else '', val_s)],
                  [cell('스포츠필드', lbl_s),
                   Table([[sf_note], [sf_tbl]], colWidths=[CW - LW])],
                  [cell('분수정원\n잼잼카페', lbl_s),
                   cell(ops_fountain.replace('\n','<br/>') if ops_fountain else '', val_s)],
              ], colWidths=[LW, CW - LW - LW])
             ]
         ], colWidths=[CW])
        ]
    ]

    ops_tbl = Table(ops_data_tbl, colWidths=[LW, CW])
    ops_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('ALIGN',       (0,0), (0,-1),  'CENTER'),
        ('BACKGROUND',  (0,0), (0,-1),  GREY),
    ]))
    story.append(ops_tbl)
    story.append(Spacer(1, 1*mm))

    # ── 4. 주차장 ────────────────────────────────────────────────
    pk_f = d.parking_family   if d else 0
    pk_d = d.parking_disabled if d else 0
    pk_p = d.parking_pregnant if d else 0
    pk_c = d.parking_children if d else 0

    parking_tbl = Table(
        [[cell('주차장', lbl_s),
          cell('다둥이 대()', lbl_s), cell(str(pk_f), val_c),
          cell('장애인 대()', lbl_s), cell(str(pk_d), val_c),
          cell('임산부 대()', lbl_s), cell(str(pk_p), val_c),
          cell('어린이단체 대()', lbl_s), cell(str(pk_c), val_c)]],
        colWidths=[LW, 22*mm, 14*mm, 22*mm, 14*mm, 22*mm, 14*mm, 26*mm, 14*mm],
        rowHeights=[9*mm],
    )
    parking_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND',  (0,0), (0,0), GREY),
        ('BACKGROUND',  (1,0), (1,0), GREY),
        ('BACKGROUND',  (3,0), (3,0), GREY),
        ('BACKGROUND',  (5,0), (5,0), GREY),
        ('BACKGROUND',  (7,0), (7,0), GREY),
    ]))
    story.append(parking_tbl)

    # ── 5. 편익시설 매출 ─────────────────────────────────────────
    e_sales = f'{eoulrim_report.daily_net_sales:,}' if eoulrim_report else '-'
    j_sales = f'{jamjam_report.daily_net_sales:,}'  if jamjam_report  else '-'
    k_sales = f'{kumnare_report.sales_amount:,}'    if kumnare_report else '-'

    facility_tbl = Table(
        [[cell('편익시설\n매출', lbl_s),
          cell('카페어울림', lbl_s), cell(e_sales, val_c),
          cell('잼잼카페',   lbl_s), cell(j_sales, val_c),
          cell('꿈나래마켓', lbl_s), cell(k_sales, val_c)]],
        colWidths=[LW, 22*mm, (W-LW-44*mm)/3, 22*mm, (W-LW-44*mm)/3, 22*mm, (W-LW-44*mm)/3],
        rowHeights=[9*mm],
    )
    facility_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND',  (0,0), (0,0),  GREY),
        ('BACKGROUND',  (1,0), (1,0),  GREY),
        ('BACKGROUND',  (3,0), (3,0),  GREY),
        ('BACKGROUND',  (5,0), (5,0),  GREY),
    ]))
    story.append(facility_tbl)

    # ── 6. 내부행사 / 외부행사 ───────────────────────────────────
    ie = (d.internal_event if d else '') or ''
    ee = (d.external_event if d else '') or ''

    for label, text in [('내부행사\n프로그램', ie), ('외부행사', ee)]:
        t = Table([[cell(label, lbl_s), cell(text.replace('\n','<br/>'), val_s)]],
                  colWidths=[LW, CW], rowHeights=[8*mm if not text else None])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT),
            ('BOX',      (0,0), (-1,-1), 0.5, BLACK),
            ('INNERGRID',(0,0), (-1,-1), 0.3, MGREY),
            ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN',    (0,0), (0,0),   'CENTER'),
            ('BACKGROUND', (0,0), (0,0), GREY),
        ]))
        story.append(t)

    # ── 7. 특이사항 ──────────────────────────────────────────────
    sn = (d.special_notes if d else '') or ''
    shuttle   = info_report.shuttle_total if info_report else '-'
    rental    = kumnare_report.rental_total_users if kumnare_report else '-'
    stamp     = kumnare_report.stamp_issued if kumnare_report else '-'

    detail_inner = Table(
        [[cell('셔틀버스', lbl_s),   cell(f'{shuttle}명', val_c),
          cell('꿈나래마켓 대여물품', lbl_s), cell(f'{rental}명', val_c),
          cell('스탬프 투어', lbl_s), cell(f'{stamp}명', val_c)]],
        colWidths=[24*mm, 22*mm, 36*mm, 22*mm, 24*mm, CW-128*mm],
        rowHeights=[7*mm],
    )
    detail_inner.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT), ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('BACKGROUND',  (0,0), (0,0), GREY),
        ('BACKGROUND',  (2,0), (2,0), GREY),
        ('BACKGROUND',  (4,0), (4,0), GREY),
    ]))
    detail_label = Paragraph('○ 세부 이용현황', ParagraphStyle('dl', fontName=FONT, fontSize=7.5, leading=10))

    special_tbl = Table(
        [[cell('특이사항', lbl_s),
          Table([[cell(sn.replace('\n','<br/>'), val_s)],
                 [detail_label],
                 [detail_inner]], colWidths=[CW])]],
        colWidths=[LW, CW],
    )
    special_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('ALIGN',       (0,0), (0,0),   'CENTER'),
        ('BACKGROUND',  (0,0), (0,0),   GREY),
    ]))
    story.append(special_tbl)
    story.append(Spacer(1, 2*mm))

    # ── 8. 비상연락 ──────────────────────────────────────────────
    emergency_s = ParagraphStyle('em', fontName=FONT, fontSize=6.5, leading=9)
    emg = Table(
        [[Paragraph('비상\n연락', lbl_s),
          Paragraph('운영대행', lbl_s),
          Paragraph('(총괄) 이정환 팀장  010-6395-8035\n(운영) 김인경 과장  010-2039-0827', emergency_s),
          Paragraph('LH', lbl_s),
          Paragraph('(운영총괄) 이원영 차장  010-9047-0752\n(대외협의) 김수민 과장  010-3928-8627', emergency_s)]],
        colWidths=[LW, 18*mm, 68*mm, 10*mm, CW-96*mm],
        rowHeights=[12*mm],
    )
    emg.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), FONT),
        ('BOX',         (0,0), (-1,-1), 0.5, BLACK),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, MGREY),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',       (2,0), (2,0),   'LEFT'),
        ('ALIGN',       (4,0), (4,0),   'LEFT'),
        ('LEFTPADDING', (2,0), (2,0),   4),
        ('LEFTPADDING', (4,0), (4,0),   4),
        ('BACKGROUND',  (0,0), (0,0), GREY),
        ('BACKGROUND',  (1,0), (1,0), GREY),
        ('BACKGROUND',  (3,0), (3,0), GREY),
    ]))
    story.append(emg)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    doc.build(story)
    return buf.getvalue()


def build_weekly_pdf(days, week_start, week_end):
    """주간 통합 PDF bytes. days는 {date: [report, ...]} 딕셔너리."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    story = []
    # 표지
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('주간 업무보고서', COVER_S))
    story.append(Paragraph(
        f'{week_start}  ~  {week_end}', COVER2_S))
    total = sum(len(v) for v in days.values())
    story.append(Paragraph(f'총 {total}건', COVER2_S))
    story.append(PageBreak())

    first_page = True
    for day, day_reports in days.items():
        if not day_reports:
            continue
        if not first_page:
            story.append(PageBreak())
        first_page = False

        # 날짜 구분 헤더
        story.append(Paragraph(
            day.strftime('%Y년 %m월 %d일 (%A)'),
            _s(f'd{day}', fontSize=13, leading=18, spaceAfter=2,
               textColor=BLUE, borderPad=2)))
        story.append(HRFlowable(width='100%', thickness=1.5, color=BLUE))
        story.append(Spacer(1, 4*mm))

        for j, report in enumerate(day_reports):
            story.extend(_report_story(report))
            if j < len(day_reports) - 1:
                story.append(Spacer(1, 6*mm))
                story.append(HRFlowable(width='100%', thickness=0.5,
                                        color=colors.HexColor('#adb5bd'), dash=(4, 2)))
                story.append(Spacer(1, 4*mm))

    doc.build(story)
    return buf.getvalue()
