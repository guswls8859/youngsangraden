# 버전 관리 기록

용산어린이정원 운영관리 시스템 변경 이력

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
