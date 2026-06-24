# 버전 관리 기록

용산어린이정원 운영관리 시스템 변경 이력

---

## [1.1.6] - 2026-06-09

### 변경
- **보류 업무 UI 가독성 개선** ([templates/reports/task_calendar.html](templates/reports/task_calendar.html))
  - 보류 상태에서 "진행중" 버튼 라벨을 **"재개"**로 변경 (완료→진행중 케이스는 그대로 "진행중" 유지)
  - 보류 상태일 때 목표 완료일을 D-Day 카운트 대신 **"⏸ 보류중"**으로 표기, 기존 목표일은 옆에 작게 표시
  - 보류중 라벨에 "보류 해제 시 보류한 일수만큼 목표일이 연장됩니다" 툴팁 추가

---

## [1.1.5] - 2026-06-09

### 추가
- **보류 → 재개 시 목표 완료일 자동 연장** ([reports/views.py:289](reports/views.py#L289))
  - `DailyTask.hold_started_at` (DateField, nullable) 추가 — 보류 진입 시 오늘 날짜 기록
  - 보류 상태에서 진행중/완료로 전환할 때 보류 일수만큼 `end_date`를 자동 연장하고 `hold_started_at`을 클리어
  - 연장이 발생한 경우 클라이언트 alert로 사용자에게 안내 ("보류 N일 동안의 기간만큼 목표 완료일이 연장되었습니다")
  - `end_date`가 없는 업무는 연장 대상 아님 (목표일이 없으므로 늘릴 게 없음)
  - AJAX 응답에 `extended_days`, `end_date`, `hold_started_at` 포함

### 마이그레이션
- `reports/migrations/0018_dailytask_hold_started_at.py`

---

## [1.1.4] - 2026-06-09

### 추가
- **업무 캘린더에 날씨 표시** — 전체일정/개인업무 캘린더의 각 날짜 셀 우상단에 일별 날씨 표시
  - 오늘부터 이달말까지(최대 16일) 데이터 노출
  - 표시 항목: 날씨 이모지(☀️🌤⛅☁️🌦🌧🌨⛈) + 최고/최저 기온(빨강/파랑) + 강수확률 30% 이상이면 💧%
  - Open-Meteo API 사용 (무료, 키 불필요), 1시간 메모리 캐시
  - 과거 날짜는 표시 안 함

### 변경
- **`reports/weather.py` 확장**
  - 신규 함수 `fetch_weather_range(start_date, end_date)` — 날짜 범위 조회 (Open-Meteo)
  - 신규 함수 `weather_label(code)` — WMO weather_code → 한국어 라벨 + 이모지 매핑
  - 기존 `fetch_tomorrow_weather()`는 그대로 유지

---

## [1.1.3] - 2026-06-08

### 추가
- **SubTask 완료일 필드** — `SubTask.completed_date` (DateField, nullable) 추가
  - 서브업무 체크 시 오늘 날짜 자동 기록, 체크 해제 시 NULL
  - 일일 업무 보고가 "그 날 완료된" 서브업무만 표시하도록 필터링
  - `reports/migrations/0016_subtask_completed_date.py`

### 변경
- **일일 업무 보고 — 사용자별 그룹 카드로 재구성** ([templates/reports/task_manager_report.html](templates/reports/task_manager_report.html))
  - 기존: 업무마다 한 행 → 같은 직원이 N건이면 이름 N번 노출
  - 변경: 직원별 카드 1개씩 표시, 클릭하면 펼쳐서 완료/진행 중 업무 확인
  - 카드 헤더에 완료(서브 N) / 진행 배지, 우상단 "모두 펼치기 / 접기" 버튼
- **"명일 진행 예정" → "진행 중인 업무" 라벨 변경**
  - 요약 카드: "진행 예정" → "진행 중"
  - 섹션 제목 및 빈 상태 문구 동일 변경
  - PDF (`reports/pdf.py`) 라벨 "익일업무계획" → "진행중인 업무"
- **완료된 서브업무 노출** — 진행 중 메인 업무에 해당 날짜에 완료된 서브업무가 있으면 완료 섹션에 함께 표시
  - 표시 형식: `[서브] [메인업무명] 서브업무 제목`
  - PDF/HTML 모두 적용
  - 완료 수치도 `완료 메인 + 완료 서브` 합산 (서브 N건 보조 표시)
- **쿼리 최적화** — 일일/주간 보고와 PDF 쿼리에 `prefetch_related('subtasks')` 추가로 N+1 방지

---

## [0.7.2] - 2026-06-01

### 변경
- **스포츠필드 인원 집계 버그 수정** — 일일보고 한글(HWP) 출력 시 입장인원에 성인·어린이 합산이 누락되던 문제 해결
  - `_sf_slot()` 입장인원 조건이 `actual_adult_count`만 체크해서 어린이만 입력된 슬롯이 무시되던 문제 → 성인 또는 어린이 중 하나라도 입력되면 합산 표시
  - `_sf_slot()` Reservation fallback에서 `actual`이 성인만 반환되던 문제 → 성인+어린이 합산
  - `_sf_day_total_by_cat()` 일반 카테고리 일일 합계에서 Reservation-only 항목의 어린이가 누락되던 문제 → 성인+어린이 합산
  - 결과: 같은 슬롯에 성인 10명·어린이 5명을 입력했을 때 일부 경로에서 10명만 합산되던 버그가 정상적으로 15명으로 출력됨

---

## [0.7.1] - 2026-05-18

### 변경
- **휴가 승인 페이지 처리 버튼 UI 수정** — 승인/반려 버튼이 좁은 컬럼에 끼어 글자가 세로로 쪼개지던 문제 해결
  - 처리 컬럼 폭을 `width:1%` → `min-width:140px`로 변경, 신청자/휴가 종류/기간/신청일시/상태 컬럼에도 `min-width` 부여
  - `btn-group` 제거 → 개별 `btn`을 `ms-1`로 분리 (그룹 강제 압축 회피)
  - `.action-btn` 클래스 추가: `white-space: nowrap`, `min-width: 58px`로 가로 정렬 고정
  - 기간/신청일시 셀에 `text-nowrap` 적용, 사유는 `.reason-cell` 클래스로 자연스러운 줄바꿈 처리

---

## [0.7.0] - 2026-05-18

### 추가
- **휴가 신청 / 승인 시스템** — 직원이 휴가를 신청하면 관리자가 검토 후 승인·반려
  - 새 모델 `VacationRequest` — 휴가 종류(연차/반차/반반차/병가/기타), 시작·종료일, 반차 시간대(오전/오후), 사유, 상태(대기/승인/반려), 검토자·검토일시·검토 메모
  - 개인업무 화면 상단에 "휴가 신청" 버튼 + 모달 (휴가 종류에 따라 종료일/시간대 자동 노출)
  - "내 휴가 내역" 페이지 — 본인 신청 전체 목록·상태·검토 결과, 대기 건은 본인 취소 가능
  - 관리자 "휴가 승인" 페이지 — 상태별 필터 탭(대기/승인/반려/전체), 승인·반려 시 검토 메모 입력 모달
  - navbar 관리자 드롭다운에 "휴가 승인" 메뉴 + 대기 건수 배지 (컨텍스트 프로세서 `pending_vacation_count`)
- **당직 근무 관리** — 관리자가 월 단위 캘린더에서 당직자 등록
  - 새 모델 `DutyShift` — `unique_together=(user, date)` 중복 방지
  - 관리자 "당직 관리" 페이지 — 월 캘린더, 셀 클릭 시 모달에서 등록/삭제, AJAX로 즉시 갱신
  - navbar 관리자 드롭다운에 "당직 관리" 메뉴
- **전체일정 / 개인업무 캘린더에 휴가·당직 배지 표시**
  - 셀의 업무 태그 위에 별도 영역(`.cal-specials`)으로 🌴 휴가 / 🌙 당직 배지 렌더링
  - 날짜 클릭 모달에도 휴가/당직 카드 표시
  - 전체일정(team): 운영사무국 전체의 승인된 휴가 + 모든 당직 노출
  - 개인업무(personal): 본인의 승인된 휴가 + 본인 당직만 노출
  - 셀 높이 120px → 140px로 확장

### 마이그레이션
- `reports/migrations/0015_vacationrequest_dutyshift.py`

---

## [0.6.2] - 2026-05-13

### 변경
- **일일보고 폼 — 저장 안내 추가** — 자동 수집 안내 박스 하단에 "한글 다운로드 전에 반드시 저장 버튼을 먼저 눌러주세요" 빨간색 강조 문구 추가
- **시설 카드 사진 영역 — 빈 경우 숨김** — 내부시설/잔디마당/분수정원 카드에서 작업사진이 없으면 갤러리 영역(`min-height: 86px`) 자체가 렌더링 안 되도록 `{% if %}` 처리. textarea와 파일 선택 행이 자연스럽게 붙음
- **폼 섹션 간격 확장** — 다닥다닥 붙어있던 페어 row + 풀폭 카드 사이 여백 증가
  - 페어 row: `g-3` → `g-4` + 행간 `mb-4` 추가 (16px → 24px)
  - 풀폭 카드(행사·특이사항): `mb-3` → `mb-4`

---

## [0.6.1] - 2026-05-13

### 변경
- **Dockerfile — 미디어 디렉토리 생성** — Cloudtype 배포 시 `/app/media` 권한 오류로 작업사진 업로드 실패하던 문제 해결
  - `mkdir -p /app/media && chmod -R 777 /app/media` 추가
- **HWPX 작업사진 표 — 1장 사진 행 전체 폭 확장** — 행에 사진이 1장만 남을 때 빈 셀 대신 `colSpan=2`로 합쳐서 표 전체 폭 차지
  - 마지막 셀의 `cellSz/width` 합산 + `cellSpan/colSpan` 갱신

---

## [0.6.0] - 2026-05-13

### 추가
- **일일보고 폼 — 편익시설 매출 / 세부 이용현황 수기 입력** — 해당 시설(`EoulrimReport`/`JamjamReport`/`KumnareReport`) 또는 안내센터(`InfoReport`) 보고서가 없는 날에 직접 수기 입력 가능
  - `OperationsDailyData`에 `manual_eoulrim_sales`, `manual_jamjam_sales`, `manual_kumnare_sales` + `manual_shuttle_total`, `manual_rental_total`, `manual_stamp_total` 추가
  - 자동 보고서 우선, 없으면 수기값 fallback (HWPX 출력에도 동일 적용)
  - 입력값 콤마 자동 포맷팅 (서버에서 콤마 제거 후 정수 변환)
- **내부행사 / 외부행사 동적 항목** — 행사명 + 사용자 정의 컬럼(헤더/값) 자유 추가 UI
  - 새 모델 `InternalEvent`, `ExternalEvent` (둘 다 `columns_json`으로 자유 컬럼 저장)
  - 폼에서 가로 표 형식 렌더링, 헤더 input 안쪽에 컬럼 삭제 ✕ 오버레이
  - HWPX 출력: sample2 nested table 템플릿 기반, N열 자동 조정
- **운영관리 작업사진 (구역별)** — 내부시설/잔디마당/분수정원 각각에 사진 N장 업로드 + 캡션 입력
  - 새 모델 `FacilityWorkPhoto` (category: interior/outdoor/fountain)
  - `OperationsDailyData`에 `facility_*_caption` 3개 필드 추가
  - HWPX 출력: sample1 기반, 카테고리별 사진 표(헤더 + 2열 이미지 + 캡션) 메인 표 뒤에 추가
  - 사진 ID 글로벌 카운터로 BinData/manifest 동기화, 미사용 ID 자동 제거
  - 사진 1장만 있을 때 빈 셀/빈 행 자동 제거
- **HWPX 자동 부착 — "○" 접두사** — 내부시설/잔디마당/분수정원 작업내용 텍스트 줄마다 "○ " 자동 부착
- **HWPX 세부 이용현황 값 채우기** — 메인 표 row 15 nested table(셔틀버스/대여물품/스탬프투어)에 보고서 값 또는 수기값 출력
- **Django admin UI 구성** — 모든 앱(parking/reports/info/facilities/sportsfield)에 ModelAdmin 등록
  - `OperationsDailyData` admin에 fieldset 섹션화 + 작업사진/이벤트 인라인 + 사진 미리보기 썸네일
  - admin 사이트 헤더 "용산어린이정원 운영관리 시스템"으로 변경

### 변경
- **Whitenoise 정적파일 서빙** — 운영(`DEBUG=False`) 환경에서 admin UI가 깨지던 문제 해결
  - `requirements.txt`에 `whitenoise==6.8.2` 추가, `WhiteNoiseMiddleware` + `CompressedManifestStaticFilesStorage` 설정
- **일일보고 폼 레이아웃 재구성** — 좌·우 컬럼 페어 row 방식으로 변경
  - Row 1: 금일 방문현황 | 내부시설
  - Row 2: 전일·기상 | 잔디마당
  - Row 3: 주차장 | 분수정원
  - Row 4: 편익시설 매출 | 세부 이용현황
  - 풀폭: 행사 (내부/외부 2분할) → 특이사항
  - `align-items: flex-start`로 카드를 자연 콘텐츠 크기 유지

### 마이그레이션
- `reports/migrations/0010` ~ `0014` (OperationsDailyData 필드 추가, InternalEvent/ExternalEvent/FacilityWorkPhoto 모델 생성)

---

## [0.5.0] - 2026-05-13

### 변경
- **GODATA 스크래퍼 방어 로직 추가** — 시간대별/구역비교/조회 클릭이 하나라도 실패하면 `nav_ok=False`로 표시하고 게이트/시간대 필드(`main_gate_walk`, `sub_gate_walk`, `slot_*` 24필드)는 DB에 저장하지 않음
  - 클릭 실패 시 대시보드 화면의 잘못된 값(총입장/총퇴장, 행번호)이 게이트 데이터로 저장되던 버그 해결
  - `today_total` / `godata_total`은 대시보드에서 안정적으로 읽히므로 항상 갱신
  - 완료 로그에 `nav=True/False` 표시
- **입장 총수 계산식 변경** — 일일보고 입력 폼에서 주출입구·부출입구·차량방문 어느 칸이든 수정하면 입장 총수에 실시간 반영
  - 백엔드: `today_total = main_gate_walk + sub_gate_walk + car_visit` (기존: `godata_total + car_visit`)
  - 프론트엔드: 주출입구/부출입구 input에 id 부여, JS가 세 칸 모두 listen
  - 라벨 안내문 갱신: "주출입구 + 부출입구 + 차량방문 자동 합산"
- **엑셀 다운로드 필터 추가** — 시간대별 데이터(`slot_*` 필드)가 하나도 없는 행은 엑셀에 포함하지 않음
  - GODATA 자동수집 실패로 시간대별 값이 비어있는 날짜(예: 4/20)가 엑셀에 끼어들지 않음

---

## [0.4.3] - 2026-05-13

### 변경
- **한글 파일 인원수 천 단위 콤마 포맷 적용** — `hwpx_report.py`에 `_fmt_num()` 헬퍼 추가, 다음 항목들이 `1,000` 형식으로 출력되도록 변경
  - 금일 방문현황: 입장 총수, 주출입구, 부출입구, 차량
  - 전일 방문현황: 입장 총수
  - 주차장: 다둥이, 장애인, 임산부, 어린이단체
  - 스포츠필드: 예약/실인원 (`_sf_val` 함수에 콤마 포맷 통합)

---

## [0.4.2] - 2026-05-13

### 변경
- **방문객 통계 엑셀 파일명 형식 변경** — 다운로드 파일명을 `(중앙일보)용산어린이정원_방문객 통계_YYMMDD.xlsx` 형식으로 통일 (한글 파일명 URL 인코딩 처리)
- **엑셀 신규 데이터 삽입 위치 버그 수정** — `ws.max_row`가 빈 스타일 행을 포함해 데이터가 엉뚱한 위치(110행 등)에 추가되던 문제 해결
  - A열에 실제 값이 있는 마지막 데이터 행을 직접 추적하도록 변경
- **엑셀 합계 행 처리 로직 추가** — 기준 파일 마지막의 합계 행(`=SUM(X2:X98)`)을 감지하고, 신규 데이터를 합계 행 **위에** 삽입한 뒤 SUM 수식 범위(B~P열)를 새 마지막 데이터 행까지 자동 확장

---

## [0.4.1] - 2026-04-21

### 추가
- **방문객 통계 엑셀 다운로드** — 기준 파일(`reports/excel_base/방문객통계_기준.xlsx`)을 베이스로 DB의 신규 날짜 데이터만 아래에 추가하는 append 방식 구현
  - 파일명 형식: `(중앙일보)용산어린이정원_방문객 통계_YYMMDD.xlsx`
  - B열 합계는 `=SUM(C:M)` 수식, 날짜 포맷·테두리·폰트 2행 스타일 복사
  - `requirements.txt`에 `openpyxl==3.1.5` 추가
- **GODATA 시간대별 입장 데이터 수집 및 저장** — `_parse_time_slots()` 추가, 구역비교 조회 후 09:00~20:00 시간대별 주출입구·부출입구 입장 인원 파싱
  - `OperationsDailyData`에 `slot_HHMM_main` / `slot_HHMM_sub` 24개 필드 추가 (nullable)
  - `reports/migrations/0009_add_timeslot_fields.py` 마이그레이션
  - `[SLOT-TEST]` INFO 로그로 파싱 과정 전체 출력 (테스트 모드)

---

## [0.3.0] - 2026-04-20

### 추가
- **스포츠필드 예약 카테고리 '일반' 추가** — `SportsfieldEntry.CATEGORY_CHOICES`에 `('normal', '일반')` 추가, 엔트리 생성 폼 기본값 변경
  - `sportsfield/migrations/0008_add_normal_category.py` 마이그레이션

### 변경
- **GODATA 토요일 수집 버그 수정** — 토요일에 주간 누적합이 앞에 추가되어 인덱스가 밀리는 문제 해결 (`found[0]`/`found[2]` → `found[-4]`/`found[-2]`)
- **GODATA 일요일 자동수집 추가** — `scheduler.py`에 일요일 17:30 CronTrigger 등록 (기존: 평일 17:30 / 토요일 20:30)
- 통합일일보고 자동수집 안내 문구 갱신 — "평일·일요일 17:30, 토요일 20:30"

---

## [0.2.3] - 2026-04-16

### 변경
- **Cloudtype Dockerfile 배포 안정화** — staticfiles 디렉토리 권한 설정(`chmod 777`), `HOME=/tmp` 설정으로 gunicorn 소켓 경로 오류 해결, `--pid /tmp/gunicorn.pid` 추가
- **GODATA 스크래퍼 클릭 안정화** — 대시보드·구역비교·조회 버튼에 `force=True` 강제 클릭 및 텍스트 기반 셀렉터 fallback 추가 (ExtJS 동적 ID 대응)
- **신규 배포 도메인 등록** — `port-0-test-mnr0z8y3c0b4fb14.sel3.cloudtype.app` ALLOWED_HOSTS·CSRF_TRUSTED_ORIGINS 추가

---

## [0.1.1] - 2026-04-15

### 변경
- **GODATA 스크래퍼 안정화** — 구역비교·조회 버튼 클릭 실패 시 텍스트 fallback 추가, 고정 타임아웃 방식으로 복구
- **입장 총수 계산 방식 개선** — `OperationsDailyData`에 `godata_total` 필드 추가, 입장 총수 = GODATA 도보 합계 + 차량방문 자동 합산
  - GODATA 재수집 시 차량방문 수치를 유지하면서 총수 재계산
  - 통합일일보고 폼의 입장 총수 칸을 읽기 전용 + 차량방문 변경 시 실시간 자동 갱신(JS)
- **HWPX 한글 파일 방문현황 데이터 출력 수정** — 주출입구·부출입구·차량방문 값이 출력되지 않던 버그 수정 (행/셀 인덱스 오류)

---

## [0.1.0] - 2026-04-15

### 추가
- **GODATA 피플카운트 자동수집** — Playwright(Headless Chromium)로 godata.co.kr 로그인 후 금일 입장 총수 파싱
  - `reports/godata_scraper.py` : 스크래핑 및 DB 저장 로직
  - `reports/scheduler.py` : APScheduler 스케줄 등록 (평일 17:30 / 토요일 20:30 자동 실행)
  - `reports/apps.py` : AppConfig.ready()에서 서버 기동 시 스케줄러 자동 시작
  - `reports/management/commands/fetch_godata_visitors.py` : 수동 실행용 관리 명령어
- 통합일일보고 화면 상단에 자동수집 안내 문구 추가 (수집 시각, 마지막 저장 시각 표시)
- `requirements.txt`에 `apscheduler==3.11.2` 추가

---

## [0.0.2] - 2026-04-15

### 추가
- `DailyTask` 모델에 검토 완료 필드 추가 (`is_reviewed`, `reviewed_by`, `reviewed_at`)
- 업무 검토 토글 뷰 및 URL (`reports:task_review`)
- 주간 보고 / 일일 관리자 보고 템플릿에 검토 상태 표시
- 이벤트하우스 메인 화면 UI 개선

### 변경
- `reports/views.py` : 검토 관련 뷰 로직 추가

---

## [0.0.1] - 2026-04-10

### 추가
- `User` 모델에 이모지 필드 추가 (`emoji`) 및 이모지 설정 뷰
- `DailyTask` 모델에 목표 완료일(`end_date`), 완료일(`completed_date`) 필드 추가
- 투두 캘린더 대폭 개선 (날짜별 업무 조회, 진행률 UI 개선)
- 기상청 단기예보 API 연동 설정 (`KMA_API_KEY`)

### 변경
- `reports/views.py` : 캘린더·투두 뷰 전면 리팩터링
- `reports/urls.py` : 캘린더 관련 URL 추가

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
