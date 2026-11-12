"""APScheduler 스케줄 설정

자동 수집 시각:
  - GODATA 입장객:  평일 17:50 / 토요일 20:50 / 일요일 17:50 KST
  - 스포츠필드 예약: 10분 간격 (API)

여러 gunicorn 워커가 각자 스케줄러를 띄우므로, 예약 수집은 PostgreSQL
어드바이저리 락으로 동시에 한 워커만 실행되게 한다.
"""
import logging

logger = logging.getLogger(__name__)


def start():
    """BackgroundScheduler를 시작하고 GODATA 수집 작업을 등록한다."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler(timezone='Asia/Seoul')

    # 평일(월~금) 17:50
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='mon-fri', hour=17, minute=50, timezone='Asia/Seoul'),
        id='godata_weekday',
        name='GODATA 평일 자동수집 (17:50)',
        replace_existing=True,
        misfire_grace_time=600,   # 10분 이내 늦게 실행돼도 허용
    )

    # 토요일 20:50
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='sat', hour=20, minute=50, timezone='Asia/Seoul'),
        id='godata_saturday',
        name='GODATA 토요일 자동수집 (20:50)',
        replace_existing=True,
        misfire_grace_time=600,
    )

    # 일요일 17:50
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='sun', hour=17, minute=50, timezone='Asia/Seoul'),
        id='godata_sunday',
        name='GODATA 일요일 자동수집 (17:50)',
        replace_existing=True,
        misfire_grace_time=600,
    )

    # 스포츠필드 예약 API — 10분 간격
    scheduler.add_job(
        _run_reservation_sync,
        trigger=IntervalTrigger(minutes=10, timezone='Asia/Seoul'),
        id='reservation_sync',
        name='스포츠필드 예약 API 자동수집 (10분)',
        replace_existing=True,
        max_instances=1,          # 이전 실행이 안 끝났으면 건너뜀
        coalesce=True,            # 밀린 실행은 1회로 합침
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info('자동수집 스케줄러 시작 — GODATA(평일17:50/토20:50/일17:50) + 예약API(10분)')
    return scheduler


# 예약 수집용 PostgreSQL 어드바이저리 락 키 (임의 고정값)
_RESERVATION_LOCK_KEY = 920114


def _run_reservation_sync():
    """스포츠필드 예약 API 동기화. 여러 워커 중복 실행을 어드바이저리 락으로 1개만 허용."""
    from django.db import connection
    from sportsfield.reservation_api import ReservationAPIError, sync_reservations

    try:
        with connection.cursor() as cur:
            cur.execute('SELECT pg_try_advisory_lock(%s)', [_RESERVATION_LOCK_KEY])
            if not cur.fetchone()[0]:
                logger.debug('예약 자동수집 스킵 — 다른 워커가 실행 중')
                return
            try:
                result = sync_reservations()
                logger.info('예약 자동수집 완료 — 조회 %s건, 신규 %s, 업데이트 %s',
                            result.get('fetched'), result.get('created'), result.get('updated'))
            finally:
                cur.execute('SELECT pg_advisory_unlock(%s)', [_RESERVATION_LOCK_KEY])
    except ReservationAPIError as e:
        logger.warning('예약 자동수집 실패: %s', e)
    except Exception:
        logger.exception('예약 자동수집 중 예외')


def _run_sync():
    """스케줄러가 호출하는 실제 동기화 함수."""
    from reports.godata_scraper import sync_godata_to_db
    logger.info('GODATA 자동수집 실행')
    sync_godata_to_db()
