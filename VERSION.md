# 버전 관리 기록

용산어린이정원 운영관리 시스템 변경 이력

각 버전마다 **핵심 코드 스니펫**을 포함해서 실제로 어떻게 구현됐는지 확인할 수 있게 했습니다.

---

## [1.2.0] - 2026-08-12

### 변경
- **HWPX 템플릿을 sample4 하나로 통합** ([reports/hwpx_report.py](reports/hwpx_report.py))
  - 기존: 사진 없음 → `sample3.hwpx`, 사진 있음 → `sample1.hwpx` + `sample3` 조합 (템플릿 이원화)
  - 변경: **`sample4.hwpx` 하나만 base로 사용** (방문현황 4열 + 사진 단락 완비된 통합판)
  - 사진 단락 템플릿을 sample4의 `p1`에서 직접 추출 (외부 파일 의존성 제거)
  - 사진 유무와 관계없이 원본 사진 단락은 항상 root에서 제거 → 사진 있으면 카테고리별로 새로 append
  - Zip 조립부: sample4 원본 `image1.JPEG`/`image2.JPEG` 항상 제외 + manifest에서 원본 image ID 제거 후 새 사용자 사진 파일명(`.jpeg`)으로 재등록
- **VERSION.md 전면 리라이트** — 초기 0.0.0부터 최신까지 각 버전에 핵심 소스코드 스니펫 추가

### 핵심 코드
```python
# reports/hwpx_report.py
BASE_HWPX = Path(__file__).parent / 'data' / 'sample4.hwpx'  # 통합판
_SAMPLE4_ORIG_IMAGES    = {'BinData/image1.JPEG', 'BinData/image2.JPEG'}
_SAMPLE4_ORIG_IMAGE_IDS = {'image1', 'image2'}

# build 함수 내부: 사진 단락 항상 추출 후 제거
root = ET.fromstring(sec0_bytes)
top_paras = root.findall('hp:p', NS)
photo_template = None
if len(top_paras) >= 2:
    photo_template = deepcopy(top_paras[1])
    root.remove(top_paras[1])

# zip 조립: 원본 이미지 제외 + manifest 재등록
for item in zin.infolist():
    if item.filename in _SAMPLE4_ORIG_IMAGES:
        continue
    if item.filename == 'Contents/content.hpf':
        hpf_xml = zin.read(item.filename).decode('utf-8')
        hpf_xml = _strip_manifest_items(hpf_xml, _SAMPLE4_ORIG_IMAGE_IDS)
        extra_items = [
            {'id': fname.split('/')[-1].rsplit('.', 1)[0],
             'href': fname, 'media_type': 'image/jpeg'}
            for fname in photo_assets
        ]
        if extra_items:
            hpf_xml = _inject_manifest_items(hpf_xml, extra_items)
```

---

## [1.1.9] - 2026-08-07

### 변경
- **HWPX 사진 첨부 시 방문현황 4열 양식 유지** ([reports/hwpx_report.py](reports/hwpx_report.py))
  - 이전: 작업사진이 있으면 `sample1.hwpx`(구 3열 방문현황)을 base로 사용 → 후문주차장 열 누락
  - 변경: 항상 `sample3.hwpx`(신 4열)을 base로 쓰고, 사진 단락 템플릿만 sample1에서 XML로 추출해서 append
  - `_attach_work_photos_multi()`가 외부 `photo_template` 파라미터 지원 (하위호환 유지)
  - zip 조립부: 사용자 업로드 이미지만 신규 삽입, manifest에 신규 image 참조 등록

### 핵심 코드
```python
# reports/hwpx_report.py
# 2. 기반 HWPX: 항상 sample3(신 4열 방문현황). 사진 있으면 sample1에서 템플릿만 가져옴
src_path = BASE_HWPX  # sample3
with zipfile.ZipFile(src_path, 'r') as zin:
    sec0_bytes = zin.read('Contents/section0.xml')

# 사진 있을 때 sample1에서 사진 단락 템플릿 추출
photo_template = None
if has_any_photos:
    try:
        from copy import deepcopy
        with zipfile.ZipFile(SAMPLE1_HWPX, 'r') as s1zip:
            s1_sec = ET.fromstring(s1zip.read('Contents/section0.xml'))
        s1_paras = s1_sec.findall('hp:p', NS)
        if len(s1_paras) >= 2:
            photo_template = deepcopy(s1_paras[1])
    except Exception:
        photo_template = None

# ...
if has_any_photos and photo_template is not None:
    photo_assets, manifest_items, unused_ids = _attach_work_photos_multi(
        root, photos_by_cat, captions_by_cat, headers_by_cat,
        photo_template=photo_template,
    )
```

---

## [1.1.8] - 2026-08-04

### 추가
- **GODATA 후문주차장 게이트 지원** — 2026-08~ GODATA 대시보드에 신규 추가된 "후문주차장" 게이트 데이터 수집·저장·표시
  - 모델: `OperationsDailyData.rear_gate_walk` + `slot_HHMM_rear` × 12 필드
  - 스크래퍼: "명" 패턴 6개(주/부/후문 × 입퇴), 시간대별 블록 6개 숫자 파싱, 4개 케이스 하위호환
  - view POST: `today_total = main + sub + rear + car` 자동 합산
  - 폼 UI: 4열 그리드 + JS 실시간 합산
  - 엑셀 다운로드: Q열(후문주차장) 추가, SUM 범위 B~P → B~Q 확장
  - HWPX: 신규 `sample3.hwpx` 기반, Row 3 방문현황 4열 배치 처리
- **캘린더에 공휴일 표시** — Python `holidays==0.101` 도입, 한국 공휴일·대체공휴일 자동 매핑

### 마이그레이션
- `reports/migrations/0019_operationsdailydata_rear_gate_walk_and_more.py`

### 핵심 코드

**스크래퍼 — 6개/4개 케이스 하위호환** ([reports/godata_scraper.py](reports/godata_scraper.py))
```python
# 2026-08~: 게이트 3개(주/부/후문주차장) × 입/퇴 = 6개
# 이전:      게이트 2개(주/부)          × 입/퇴 = 4개
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
```

**HWPX — 셀 개수로 자동 분기** ([reports/hwpx_report.py](reports/hwpx_report.py))
```python
# 신규 sample3(4열) / 구 sample1(3열) 모두 지원
if len(dc) >= 4:
    _set_t(dc[0], _fmt_num(main_gate_walk))  # 주출입구 도보
    _set_t(dc[1], _fmt_num(car_visit))        # 주출입구 차량방문
    _set_t(dc[2], _fmt_num(sub_gate_walk))    # 부출입구1 도보
    _set_t(dc[3], _fmt_num(rear_gate))        # 부출입구2 주차장 도보
elif len(dc) >= 3:
    # 구 3열 (하위호환)
    _set_t(dc[0], _fmt_num(main_gate_walk))
    _set_t(dc[1], _fmt_num(sub_gate_walk))
    _set_t(dc[2], _fmt_num(car_visit))
```

**공휴일 컨텍스트 주입** ([reports/views.py](reports/views.py))
```python
# 캘린더 view — 해당 월 공휴일을 JSON으로 템플릿에 전달
day_holidays = {}
try:
    import holidays as _holidays
    kr = _holidays.KR(years=year)
    for d, name in kr.items():
        if d.month == month:
            day_holidays[d.day] = str(name)
except Exception:
    pass
day_holidays_json = json.dumps(day_holidays)
```

---

## [1.1.7] - 2026-06-09

### 추가
- **작업사진 자동 압축 (클라이언트)** — Canvas API로 즉시 리사이즈 + JPEG 재인코딩
  - 긴 변 최대 1600px, JPEG 품질 0.82, 600KB 미만은 압축 생략
- **내부/외부 행사 — 행(row) 추가 기능** — 헤더 1행 + 데이터 N행 표 입력

### 변경
- **행사 데이터 구조 변경** — `columns_json` 신구 형식 호환
  - 신규: `{headers: [...], rows: [[...], [...]]}`
  - 기존: `[{header, value}, ...]`도 읽을 때 자동 변환

### 핵심 코드

**Canvas 리사이즈 + JPEG 재인코딩** ([templates/reports/integrated_daily.html](templates/reports/integrated_daily.html))
```javascript
const MAX_EDGE = 1600;
const QUALITY  = 0.82;
const SKIP_BYTES = 600 * 1024;

async function compressOne(file) {
    if (!file.type.startsWith('image/'))     return file;
    if (file.type === 'image/gif')           return file;
    if (file.size <= SKIP_BYTES)             return file;

    const img = await loadImage(file);
    const longest = Math.max(img.width, img.height);
    const scale   = longest > MAX_EDGE ? MAX_EDGE / longest : 1;
    const canvas  = document.createElement('canvas');
    canvas.width  = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', QUALITY));
    if (!blob || blob.size >= file.size) return file;  // 더 커지면 원본 사용
    const newName = file.name.replace(/\.\w+$/i, '') + '.jpg';
    return new File([blob], newName, { type: 'image/jpeg', lastModified: Date.now() });
}
```

**행사 데이터 구조 신구 형식 자동 변환** ([reports/views.py](reports/views.py))
```python
def _normalize_event_cols(raw):
    """[{header, value}] 또는 {headers, rows} 형식을 통일."""
    if not raw:
        return {'headers': [], 'rows': []}
    if isinstance(raw, dict) and 'headers' in raw:
        return {
            'headers': list(raw.get('headers') or []),
            'rows':    [list(r) for r in (raw.get('rows') or [])],
        }
    if isinstance(raw, list):
        headers = [(c.get('header') or '') for c in raw if isinstance(c, dict)]
        row     = [(c.get('value')  or '') for c in raw if isinstance(c, dict)]
        return {'headers': headers, 'rows': [row] if any(row) else []}
    return {'headers': [], 'rows': []}
```

**HWPX 데이터 행 N개 동적 생성** ([reports/hwpx_report.py](reports/hwpx_report.py))
```python
# 첫 데이터 행은 templete row에 채우고, 이후 행은 deepcopy로 append
first_row = rows_to_render[0]
for i in range(N):
    v = first_row[i] if i < len(first_row) else ''
    data_tr_tpl.append(_make_cell(tpl_data_cell, 1, i, str(v).strip(), cell_w))

for r_idx, row in enumerate(rows_to_render[1:], start=2):
    new_tr = deepcopy(data_tr_tpl)
    for j, cell in enumerate(new_tr.findall('hp:tc', NS)):
        v = row[j] if j < len(row) else ''
        _set_para_text(cell.find('hp:subList/hp:p', NS), str(v).strip())
        ca = cell.find('hp:cellAddr', NS)
        if ca is not None:
            ca.set('rowAddr', str(r_idx))
    tbl.append(new_tr)

tbl.set('colCnt', str(N))
tbl.set('rowCnt', str(1 + len(rows_to_render)))
```

---

## [1.1.6] - 2026-06-09

### 변경
- **보류 업무 UI 가독성 개선** — 라벨/색 정리
  - "진행중" 버튼 → 보류 상태에서만 **"재개"**로 표시
  - 보류 상태의 목표 완료일을 D-Day 대신 **"⏸ 보류중"** 한 줄로 간소화

### 핵심 코드
```javascript
// templates/reports/task_calendar.html
${t.status !== 'doing' ? `<button ...>${t.status === 'hold' ? '재개' : '진행중'}</button>` : ''}

// 목표일 렌더링 — 보류 시 D-Day 대신 "보류중"
if (t.status === 'hold') {
    parts.push(`<span class="text-muted" style="font-size:.7rem"
                     title="보류 해제 시 보류한 일수만큼 목표일이 연장됩니다">⏸ 보류중</span>`);
} else if (t.end_date) {
    // ... 기존 D-Day 계산 ...
}
```

---

## [1.1.5] - 2026-06-09

### 추가
- **보류 → 재개 시 목표 완료일 자동 연장**
  - `DailyTask.hold_started_at` (DateField, nullable) 추가
  - 보류에서 진행/완료 전환 시 보류 일수만큼 `end_date` 자동 연장
  - AJAX 응답에 `extended_days` 포함해서 사용자에게 alert 안내

### 마이그레이션
- `reports/migrations/0018_dailytask_hold_started_at.py`

### 핵심 코드
```python
# reports/views.py — task_update_status
today = timezone.localdate()
prev_status = task.status
new_end_date  = task.end_date
new_hold_at   = task.hold_started_at
extended_days = 0

# 보류 → 다른 상태: 보류 일수만큼 end_date 연장
if prev_status == 'hold' and status != 'hold' and task.hold_started_at:
    delta = (today - task.hold_started_at).days
    if delta > 0 and task.end_date:
        new_end_date  = task.end_date + datetime.timedelta(days=delta)
        extended_days = delta
    new_hold_at = None
# 다른 상태 → 보류 진입: 시작 시점 기록
elif status == 'hold' and prev_status != 'hold':
    new_hold_at = today
```

---

## [1.1.4] - 2026-06-09

### 추가
- **업무 캘린더에 날씨 표시** — 오늘 ~ 이달말(최대 16일) 각 셀 우상단에 이모지 + 최고/최저 기온 + 강수확률(30% ↑)
  - Open-Meteo API 사용 (무료, 키 불필요), 1시간 메모리 캐시

### 핵심 코드

**날씨 범위 조회** ([reports/weather.py](reports/weather.py))
```python
def fetch_weather_range(start_date, end_date) -> dict:
    """start~end 사이 날짜별 예보 반환 (Open-Meteo, 최대 16일)."""
    url = (
        'https://api.open-meteo.com/v1/forecast'
        f'?latitude={_LAT}&longitude={_LON}'
        '&daily=temperature_2m_max,temperature_2m_min,'
        'precipitation_probability_max,weather_code'
        '&timezone=Asia%2FSeoul'
        f'&start_date={start_date.isoformat()}&end_date={end_date.isoformat()}'
    )
    with urllib.request.urlopen(url, timeout=4) as resp:
        data = json.loads(resp.read())
    result = {}
    for i, day_str in enumerate(data['daily']['time']):
        result[datetime.date.fromisoformat(day_str)] = {
            'temp_min': round(data['daily']['temperature_2m_min'][i]),
            'temp_max': round(data['daily']['temperature_2m_max'][i]),
            'rain_pct': int(data['daily']['precipitation_probability_max'][i] or 0),
            'code':     int(data['daily']['weather_code'][i] or 0),
        }
    return result

# WMO code → 한국어 라벨 + 이모지
_WMO_CODE = {
    0: ('맑음', '☀️'), 1: ('대체로 맑음', '🌤'), 2: ('구름 조금', '⛅'), 3: ('흐림', '☁️'),
    51: ('약한 이슬비', '🌦'), 61: ('약한 비', '🌦'), 63: ('비', '🌧'),
    71: ('약한 눈', '🌨'), 95: ('뇌우', '⛈'),
    # ...
}
```

---

## [1.1.3] - 2026-06-08

### 추가
- **SubTask 완료일 필드** — `SubTask.completed_date` (DateField, nullable) 추가
  - 서브업무 체크 시 오늘 날짜 자동 기록, 체크 해제 시 NULL
  - 일일 업무 보고가 "그 날 완료된" 서브업무만 표시하도록 필터링
  - `reports/migrations/0016_subtask_completed_date.py`

### 변경
- **일일 업무 보고 — 사용자별 그룹 카드로 재구성** — 직원 이름 1번씩 노출, 클릭하면 펼쳐서 확인
- **"명일 진행 예정" → "진행 중인 업무" 라벨 변경**
- **완료된 서브업무 노출** — 진행 중 메인 업무의 해당 날짜 완료 서브업무를 완료 섹션에 함께 표시

### 핵심 코드

**서브업무 완료일 기록** ([reports/views.py](reports/views.py) `subtask_toggle`)
```python
subtask.is_done = not subtask.is_done
subtask.completed_date = timezone.localdate() if subtask.is_done else None
subtask.save()
subtask.daily_task.recalculate_progress()
```

**PDF/HTML 필터 — 그 날 완료된 서브업무만 노출**
```python
# 진행중 업무 중 target_date에 완료된 서브업무만
for t in pending_tasks:
    done_subs = [s for s in t.subtasks.all()
                 if s.is_done and s.completed_date == target_date]
    if done_subs:
        done_subtasks_by_task[t.pk] = (t, done_subs)
```

---

## [0.7.2] - 2026-06-01

### 변경
- **스포츠필드 인원 집계 버그 수정** — 성인·어린이 합산 누락 문제 해결
  - `_sf_slot()` 입장인원 조건 오류: `actual_adult_count`만 체크 → 어린이만 입력된 슬롯 무시
  - `_sf_slot()` Reservation fallback: `actual`이 성인만 반환됨
  - `_sf_day_total_by_cat()` 일반 카테고리: Reservation-only 항목의 어린이 누락

### 핵심 코드
```python
# reports/views.py — _sf_slot()
# 입장인원: actual_* 필드 (성인/어린이 둘 다 합산)
act = None
if e.actual_adult_count is not None or e.actual_child_count is not None:
    act = (e.actual_adult_count or 0) + (e.actual_child_count or 0)

# Reservation fallback도 동일하게
for r in sf_reservations:
    if r.field_type in field_types and r.time_start == start_time:
        act = None
        if r.actual_adult_count is not None or r.actual_child_count is not None:
            act = (r.actual_adult_count or 0) + (r.actual_child_count or 0)
        return {'cat': '일반', 'reserved': r.total_users, 'actual': act}
```

---

## [0.7.1] - 2026-05-18

### 변경
- **휴가 승인 페이지 처리 버튼 UI 수정** — 승인/반려 버튼이 좁은 컬럼에 끼어 글자 세로 쪼개지던 문제
  - 처리 컬럼 `width:1%` → `min-width:140px`
  - `btn-group` 제거 → 개별 `btn`을 `ms-1`로 분리
  - `.action-btn` 클래스: `white-space: nowrap`, `min-width: 58px`

### 핵심 코드
```html
<!-- templates/reports/vacation_admin_list.html -->
<style>
.action-btn {
    white-space: nowrap;
    min-width: 58px;
    font-size: .8rem;
}
</style>
<button class="btn btn-sm btn-success action-btn" ...>
    <i class="bi bi-check-lg"></i> 승인
</button>
<button class="btn btn-sm btn-outline-danger action-btn ms-1" ...>
    <i class="bi bi-x-lg"></i> 반려
</button>
```

---

## [0.7.0] - 2026-05-18

### 추가
- **휴가 신청 / 승인 시스템** — 직원 신청 → 관리자 검토
  - 새 모델 `VacationRequest` (연차/반차/반반차/병가/기타, 오전/오후, 대기/승인/반려)
  - 개인업무 화면에 "휴가 신청" 버튼 + 모달
  - 관리자 "휴가 승인" 페이지 (상태별 필터 탭, 검토 메모 입력)
  - navbar에 대기 건수 배지 (컨텍스트 프로세서)
- **당직 근무 관리** — 관리자 월 캘린더에서 등록
  - 새 모델 `DutyShift` (`unique_together=(user, date)`)
- **전체일정/개인업무 캘린더에 휴가·당직 배지** — 🌴 휴가 / 🌙 당직

### 마이그레이션
- `reports/migrations/0015_vacationrequest_dutyshift.py`

### 핵심 코드

**모델** ([reports/models.py](reports/models.py))
```python
class VacationRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('annual','연차'), ('half','반차'), ('quarter','반반차'),
        ('sick','병가'), ('etc','기타'),
    ]
    HALF_PERIOD_CHOICES = [('am','오전'), ('pm','오후')]
    STATUS_CHOICES = [
        ('pending','대기'), ('approved','승인'), ('rejected','반려'),
    ]
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    leave_type      = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES)
    start_date      = models.DateField()
    end_date        = models.DateField()
    half_period     = models.CharField(max_length=2, choices=HALF_PERIOD_CHOICES, blank=True)
    reason          = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by     = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, ...)
    reviewed_at     = models.DateTimeField(null=True, blank=True)
    review_comment  = models.TextField(blank=True)

class DutyShift(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    date       = models.DateField()
    note       = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, ...)

    class Meta:
        unique_together = ['user', 'date']
```

**컨텍스트 프로세서 — 관리자 대기 건수 배지** ([reports/context_processors.py](reports/context_processors.py))
```python
def vacation_pending_count(request):
    if (not request.user.is_authenticated
        or request.user.organization != 'operations'
        or request.user.role != 'manager'):
        return {}
    count = VacationRequest.objects.filter(status='pending').count()
    return {'pending_vacation_count': count}
```

---

## [0.6.2] - 2026-05-13

### 변경
- **일일보고 폼 — 저장 안내 추가** — "한글 다운로드 전에 반드시 저장 버튼을 먼저 눌러주세요" 빨간색 강조 문구
- **시설 카드 사진 영역 — 빈 경우 숨김** — 갤러리 영역 자체를 `{% if %}`로 제거
- **폼 섹션 간격 확장** — `g-3 → g-4`, `mb-3 → mb-4` (16px → 24px)

### 핵심 코드
```html
<!-- HWP 다운로드 dirty check (JS로 변경 감지 후 버튼 비활성화 + 경고) -->
<script>
let dirty = false;
function setDirty() { dirty = true; }
form.querySelectorAll('input, textarea, select').forEach(el => {
    el.addEventListener('change', setDirty);
    el.addEventListener('input', setDirty);
});
hwpBtns.forEach(btn => btn.addEventListener('click', e => {
    if (dirty) {
        e.preventDefault();
        alert('변경된 내용이 있습니다. 저장 버튼을 먼저 눌러주세요.');
    }
}));
</script>
```

---

## [0.6.1] - 2026-05-13

### 변경
- **Dockerfile — 미디어 디렉토리 생성** — Cloudtype `/app/media` 권한 오류로 사진 업로드 실패하던 문제
  ```dockerfile
  RUN mkdir -p /app/staticfiles /app/media && chmod -R 777 /app/staticfiles /app/media
  ```
- **HWPX 작업사진 표 — 1장 사진 행 전체 폭 확장** — 마지막 셀 `cellSz/width` 합산 + `cellSpan/colSpan` 갱신
  ```python
  # reports/hwpx_report.py — _fill_photo_paragraph
  PER_ROW = 2
  cells_in_last = used - (needed_rows - 1) * PER_ROW if needed_rows else 0
  if remaining and cells_in_last < PER_ROW and cells_in_last > 0:
      last_row = remaining[-1]
      last_cells = last_row.findall('hp:tc', NS)
      extra_width = 0
      for c in last_cells[cells_in_last:]:
          cs = c.find('hp:cellSz', NS)
          if cs is not None:
              extra_width += int(cs.get('width') or 0)
          last_row.remove(c)
      kept_cell = last_cells[cells_in_last - 1]
      cs = kept_cell.find('hp:cellSz', NS)
      if cs is not None and extra_width:
          cs.set('width', str(int(cs.get('width') or 0) + extra_width))
      sp = kept_cell.find('hp:cellSpan', NS)
      if sp is not None:
          sp.set('colSpan', str(int(sp.get('colSpan') or 1) + (PER_ROW - cells_in_last)))
  ```

---

## [0.6.0] - 2026-05-13

### 추가
- **일일보고 폼 — 편익시설 매출 / 세부 이용현황 수기 입력** — 시설 보고서 없는 날 직접 입력
- **내부/외부 행사 동적 항목** — 새 모델 `InternalEvent` / `ExternalEvent` (`columns_json` JSONField)
- **운영관리 작업사진 (구역별)** — 새 모델 `FacilityWorkPhoto` (interior/outdoor/fountain)
- **HWPX 자동 부착 — "○" 접두사** — 각 줄 앞에 자동 부착
- **Django admin UI 구성** — 모든 앱 ModelAdmin 등록

### 변경
- **Whitenoise 정적파일 서빙** — 운영(`DEBUG=False`) admin UI 깨지던 문제
- **일일보고 폼 레이아웃 재구성** — 좌·우 컬럼 페어 row 방식

### 마이그레이션
- `reports/migrations/0010` ~ `0014`

### 핵심 코드

**행사·작업사진 모델** ([reports/models.py](reports/models.py))
```python
class InternalEvent(models.Model):
    ops = models.ForeignKey(OperationsDailyData, related_name='internal_events', ...)
    name = models.CharField(max_length=200)
    columns_json = models.JSONField(default=list, blank=True)  # 자유 컬럼
    order = models.PositiveIntegerField(default=0)

class FacilityWorkPhoto(models.Model):
    CATEGORY_CHOICES = [
        ('interior','내부시설'),
        ('outdoor', '잔디마당·가로수길·전망언덕'),
        ('fountain','분수정원·잼잼카페'),
    ]
    ops      = models.ForeignKey(OperationsDailyData, related_name='work_photos', ...)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    image    = models.ImageField(upload_to='work_photos/%Y/%m/')
    order    = models.PositiveIntegerField(default=0)
```

**Whitenoise 설정** ([config/settings.py](config/settings.py))
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 신규
    # ...
]
STORAGES = {
    'default':     {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
```

**HWPX 자동 "○" 접두사** ([reports/hwpx_report.py](reports/hwpx_report.py))
```python
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
```

---

## [0.5.0] - 2026-05-13

### 변경
- **GODATA 스크래퍼 방어 로직** — 시간대별·구역비교·조회 클릭 하나라도 실패하면 `nav_ok=False` 표시 → 게이트/시간대 필드 저장 스킵
- **입장 총수 계산식 변경** — 폼에서 주/부/차량 어느 칸이든 수정하면 실시간 반영
  - 백엔드: `today_total = main_gate_walk + sub_gate_walk + car_visit`
- **엑셀 다운로드 필터 추가** — 시간대별 데이터(`slot_*`) 없는 행은 제외

### 핵심 코드

**스크래퍼 nav 방어 로직** ([reports/godata_scraper.py](reports/godata_scraper.py))
```python
nav_ok = True
if not (_try_click(page, '#ext-element-707')
        or _try_force_click(page, 'text=시간대별')):
    logger.warning('GODATA: 시간대별 탭 진입 실패')
    nav_ok = False

if nav_ok:
    # 구역비교 체크박스, 조회 버튼 클릭...
    ...

# nav_ok 실패면 대시보드 총계만 저장, 게이트/시간대 필드는 건드리지 않음
if data.get('nav_ok'):
    if data.get('main_gate_walk') is not None:
        godata_fields['main_gate_walk'] = data['main_gate_walk']
    ...
```

**입장 총수 실시간 합산 (JS)** ([templates/reports/integrated_daily.html](templates/reports/integrated_daily.html))
```javascript
function update(){
    const m = parseInt(mainInput.value) || 0;
    const s = parseInt(subInput.value)  || 0;
    const c = parseInt(carInput.value)  || 0;
    display.value = m + s + c;
}
[mainInput, subInput, carInput].forEach(el => el.addEventListener('input', update));
```

---

## [0.4.3] - 2026-05-13

### 변경
- **한글 파일 인원수 천 단위 콤마 포맷 적용** — `hwpx_report.py`에 `_fmt_num()` 헬퍼 추가

### 핵심 코드
```python
# reports/hwpx_report.py
def _fmt_num(n):
    """인원수 등 정수를 3자리마다 콤마로 변환. 0/None은 '0'."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return '0'

# 적용 대상: 금일/전일 방문현황, 주차장, 스포츠필드(예약/실인원)
```

---

## [0.4.2] - 2026-05-13

### 변경
- **엑셀 파일명 형식** — `(중앙일보)용산어린이정원_방문객 통계_YYMMDD.xlsx`
- **엑셀 신규 데이터 삽입 위치 버그 수정** — `ws.max_row`가 빈 스타일 행 포함해서 엉뚱한 위치(110행)에 추가되던 문제
- **엑셀 합계 행 처리 로직** — 마지막 SUM 행 위에 삽입 + SUM 범위 자동 확장

### 핵심 코드
```python
# reports/views.py — integrated_daily_excel
# A열에 실제 값이 있는 마지막 데이터 행 + SUM 행 위치 스캔
existing_dates = set()
last_data_row = 1
sum_row = None
for r, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
    a_val = row[0]
    b_val = row[1] if len(row) > 1 else None
    if a_val is None:
        if isinstance(b_val, str) and b_val.upper().startswith('=SUM('):
            sum_row = r
            break
        continue
    last_data_row = r
    if hasattr(a_val, 'date'):
        existing_dates.add(a_val.date())

# 합계 행 위에 n개 빈 행 삽입 → 합계 행은 sum_row+n으로 밀림
if sum_row is not None:
    ws.insert_rows(sum_row, amount=n)
    new_sum_row = sum_row + n
    # SUM 수식 범위 갱신
    for c in range(2, 17):
        col_letter = openpyxl.utils.get_column_letter(c)
        ws.cell(row=new_sum_row, column=c).value = (
            f'=SUM({col_letter}2:{col_letter}{new_sum_row - 1})'
        )

# 파일명 URL 인코딩
from urllib.parse import quote
filename = f'(중앙일보)용산어린이정원_방문객 통계_{today:%y%m%d}.xlsx'
response['Content-Disposition'] = (
    f"attachment; filename=\"visitor_stats_{today:%y%m%d}.xlsx\"; "
    f"filename*=UTF-8''{quote(filename, safe='')}"
)
```

---

## [0.4.1] - 2026-04-21

### 추가
- **방문객 통계 엑셀 다운로드** — 기준 파일 base + DB 신규 날짜 append
- **GODATA 시간대별 입장 데이터 수집** — `_parse_time_slots()` 추가, `slot_HHMM_main/sub` 24필드
- `reports/migrations/0009_add_timeslot_fields.py`

### 핵심 코드

**시간대별 파싱** ([reports/godata_scraper.py](reports/godata_scraper.py))
```python
def _parse_time_slots(body: str) -> dict:
    """
    body 구조:
        09:00 ~ 10:00
        {부출입구 입장}
        {부출입구 퇴장}   ← 저장 안 함
        {주출입구 입장}
        {주출입구 퇴장}   ← 저장 안 함
        10:00 ~ 11:00
        ...
    반환: {'slot_0900_sub': int, 'slot_0900_main': int, ...}
    """
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    TIME_RE = re.compile(r'^(\d{2}):\d{2}\s*~\s*\d{2}:\d{2}$')
    NUM_RE  = re.compile(r'^[\d,]+$')
    slot_indices = [(i, TIME_RE.match(line).group(1))
                    for i, line in enumerate(lines) if TIME_RE.match(line)]
    명_start = next((i for i, l in enumerate(lines) if '명' in l), len(lines))
    results = {}
    for idx, (line_idx, start_h) in enumerate(slot_indices):
        next_slot = slot_indices[idx + 1][0] if idx + 1 < len(slot_indices) else 명_start
        block = lines[line_idx + 1: next_slot]
        nums = [int(l.replace(',', '')) for l in block if NUM_RE.match(l)]
        if len(nums) < 3:
            continue
        results[f'slot_{start_h}00_sub']  = nums[0]
        results[f'slot_{start_h}00_main'] = nums[2]
    return results
```

---

## [0.3.0] - 2026-04-20

### 추가
- **스포츠필드 예약 카테고리 '일반' 추가** — `SportsfieldEntry.CATEGORY_CHOICES`
- `sportsfield/migrations/0008_add_normal_category.py`

### 변경
- **GODATA 토요일 수집 버그 수정** — 토요일 주간 누적합이 앞에 붙어서 인덱스 밀림
  ```python
  # 이전: found[0], found[2] (앞에서 카운트)
  # 변경: found[-4], found[-2] (뒤에서 카운트) — 항상 마지막 4개 사용
  sub_gate  = _parse_count(found[-4])
  main_gate = _parse_count(found[-2])
  ```
- **GODATA 일요일 자동수집 추가** — `scheduler.py`에 일요일 CronTrigger 추가
  ```python
  scheduler.add_job(
      _run_sync,
      trigger=CronTrigger(day_of_week='sun', hour=17, minute=30, timezone='Asia/Seoul'),
      id='godata_sunday',
      replace_existing=True,
  )
  ```

---

## [0.2.3] - 2026-04-16

### 변경
- **Cloudtype Dockerfile 배포 안정화** — `chmod 777`, `HOME=/tmp`, `--pid /tmp/gunicorn.pid`
- **GODATA 스크래퍼 클릭 안정화** — `force=True` + 텍스트 셀렉터 fallback (ExtJS 동적 ID 대응)
- **신규 배포 도메인 등록**

### 핵심 코드
```python
# reports/godata_scraper.py — 헬퍼 함수들 (0.2.3에서 도입)
def _try_click(page, selector) -> bool:
    """클릭 성공 시 True, 실패 시 False (예외 없음)."""
    try:
        page.click(selector, timeout=3000)
        return True
    except Exception:
        return False

def _try_force_click(page, selector) -> bool:
    """force=True 클릭 — 오버레이에 가려진 요소 대응."""
    try:
        page.click(selector, timeout=3000, force=True)
        return True
    except Exception:
        return False
```

```dockerfile
# Dockerfile
ENV HOME=/tmp
RUN chmod 777 /app/staticfiles
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --worker-tmp-dir /tmp \
        --pid /tmp/gunicorn.pid \
        --timeout 120
```

---

## [0.1.1] - 2026-04-15

### 변경
- **GODATA 스크래퍼 안정화** — 텍스트 fallback, 고정 타임아웃
- **입장 총수 계산 방식 개선** — `OperationsDailyData`에 `godata_total` 필드 추가
  - `today_total = godata_total + car_visit` (GODATA 재수집 시 차량방문 유지)
  - 폼 입장 총수 칸을 readonly + 차량방문 변경 시 JS 자동 갱신
- **HWPX 방문현황 데이터 출력 수정** — 주/부/차량 값이 출력되지 않던 행/셀 인덱스 오류

---

## [0.1.0] - 2026-04-15

### 추가
- **GODATA 피플카운트 자동수집** — Playwright(Headless Chromium)로 스크래핑
  - `reports/godata_scraper.py` : 스크래핑 로직
  - `reports/scheduler.py` : APScheduler 등록 (평일 17:30 / 토요일 20:30)
  - `reports/apps.py` : AppConfig.ready()에서 자동 시작
  - `reports/management/commands/fetch_godata_visitors.py` : 수동 실행
- `requirements.txt`에 `apscheduler==3.11.2` 추가

### 핵심 코드
```python
# reports/scheduler.py
def start():
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(timezone='Asia/Seoul')
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='mon-fri', hour=17, minute=50,
                            timezone='Asia/Seoul'),
        id='godata_weekday',
        replace_existing=True,
        misfire_grace_time=600,  # 10분 이내 늦게 실행돼도 허용
    )
    # 토요일 20:50, 일요일 17:50 등도 동일 방식으로 add
    scheduler.start()
    return scheduler

# reports/apps.py — 서버 기동 시 자동 시작
class ReportsConfig(AppConfig):
    def ready(self):
        from . import scheduler
        scheduler.start()
```

---

## [0.0.2] - 2026-04-15

### 추가
- `DailyTask` 모델에 검토 완료 필드 추가 (`is_reviewed`, `reviewed_by`, `reviewed_at`)
- 업무 검토 토글 뷰 및 URL (`reports:task_review`)
- 주간 보고 / 일일 관리자 보고 템플릿에 검토 상태 표시
- 이벤트하우스 메인 화면 UI 개선

### 핵심 코드
```python
# reports/models.py — DailyTask에 필드 추가
is_reviewed = models.BooleanField(default=False, verbose_name='검토 완료')
reviewed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='reviewed_tasks',
    verbose_name='검토자',
)
reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='검토 일시')
```

---

## [0.0.1] - 2026-04-10

### 추가
- `User` 모델에 이모지 필드 추가 (`emoji`) 및 이모지 설정 뷰
- `DailyTask` 모델에 목표 완료일(`end_date`), 완료일(`completed_date`) 필드 추가
- 투두 캘린더 대폭 개선 (날짜별 업무 조회, 진행률 UI 개선)
- 기상청 단기예보 API 연동 설정 (`KMA_API_KEY`)

### 핵심 코드
```python
# accounts/models.py
class User(AbstractUser):
    emoji = models.CharField(max_length=10, blank=True, verbose_name='이모지')
    # ...

# reports/models.py — DailyTask 날짜 필드
class DailyTask(models.Model):
    start_date     = models.DateField(default=timezone.localdate)
    end_date       = models.DateField(null=True, blank=True, verbose_name='목표 완료일')
    completed_date = models.DateField(null=True, blank=True, verbose_name='완료일')

    def save(self, *args, **kwargs):
        self.progress = max(0, min(100, self.progress))
        if self.progress == 100:
            self.status = 'done'
            if not self.completed_date:
                self.completed_date = timezone.localdate()
        elif self.status == 'done' and self.progress < 100:
            self.status = 'doing'
            self.completed_date = None
        super().save(*args, **kwargs)
```

---

## [0.0.0] - 초기 구축

### 구성
- **accounts** : 커스텀 유저 모델 (소속·역할 기반 접근 권한)
- **reports** : 일일 업무보고(DailyReport), 투두(DailyTask), 통합일일보고(OperationsDailyData)
- **parking** : 출입 차량 등록 및 입출차 기록
- **info** : 안내센터 보고서 (인포메이션·셔틀·순찰)
- **facilities** : 편익시설 보고서 (꿈나래마켓·카페어울림·잼잼카페)
- **sportsfield** : 스포츠필드 예약 크롤링 및 이용 실적 입력
- **eventhouse** : 이벤트하우스 공간 사용 기록
- PostgreSQL 연동, WeasyPrint PDF 출력, hwpx 한글 파일 출력

### 핵심 코드
```python
# accounts/models.py — 커스텀 유저
class User(AbstractUser):
    ROLE_CHOICES = [
        ('staff', '직원'),
        ('up_staff', '운영사무국직원'),
        ('manager', '관리자'),
    ]
    ORGANIZATION_CHOICES = [
        ('operations', '운영사무국'),
        ('parking', '보안팀'),
        ('info', '안내센터'),
        ('sportsfield', '스포츠필드'),
        ('dreammarket', '꿈나래마켓'),
        ('eulrimcafe', '카페어울림'),
        ('jemjemcafe', '잼잼카페'),
    ]
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    organization = models.CharField(max_length=20, choices=ORGANIZATION_CHOICES,
                                    default='operations')

    @property
    def can_access_operations(self):
        return self.organization == 'operations'
    # ... 소속별 permission property들
```
