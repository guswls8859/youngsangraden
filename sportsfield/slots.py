"""스포츠필드 타임 슬롯 정의 (단일 출처).

2026-11-10 개편 (sample5 양식):
  - 축구장·테니스장: 4타임 (10~12, 12~14, 14~16, 16~18)
  - 야구장:          3타임 (09~12, 12~15, 15~18)

sportsfield 입력 화면과 reports 통합 일일보고(HWPX/PDF)가 모두 이 정의를 사용한다.
"""

_ST_SLOTS = [('10:00', '12:00'), ('12:00', '14:00'), ('14:00', '16:00'), ('16:00', '18:00')]
_BB_SLOTS = [('09:00', '12:00'), ('12:00', '15:00'), ('15:00', '18:00')]

# 보고서 표 기준 그룹: soccer / tennis(잔디+하드 합산) / baseball
SLOT_GROUPS = {
    'soccer':   _ST_SLOTS,
    'tennis':   _ST_SLOTS,
    'baseball': _BB_SLOTS,
}


def slot_label(index, start, end):
    """index는 0부터. 예: slot_label(0, '10:00', '12:00') → '1타임 (10:00~12:00)'"""
    return f'{index + 1}타임 ({start}~{end})'


def _with_labels(slots):
    return [(s, e, slot_label(i, s, e)) for i, (s, e) in enumerate(slots)]


# 입력 화면용: field_type(FIELD_CHOICES 키)별 (start, end, label)
TIME_SLOTS = {
    'soccer':       _with_labels(_ST_SLOTS),
    'baseball':     _with_labels(_BB_SLOTS),
    'tennis_grass': _with_labels(_ST_SLOTS),
    'tennis_hard':  _with_labels(_ST_SLOTS),
}


# 테니스 코트 면수 — 쿼터/행사는 해당 종류 코트 전체를 쓰므로 집계 시 이 수만큼 곱한다.
# 하드코트는 원래 4면이나 현재 2면 공사중 → 복구 시 tennis_hard 값만 4로.
COURT_COUNTS = {
    'tennis_grass': 2,
    'tennis_hard':  2,
}
