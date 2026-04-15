"""APScheduler 스케줄 설정

자동 수집 시각:
  - 평일 (월~금): 17:30 KST
  - 토요일:       20:30 KST
  - 일요일:       없음
"""
import logging

logger = logging.getLogger(__name__)


def start():
    """BackgroundScheduler를 시작하고 GODATA 수집 작업을 등록한다."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler(timezone='Asia/Seoul')

    # 평일(월~금) 17:30
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='mon-fri', hour=17, minute=30, timezone='Asia/Seoul'),
        id='godata_weekday',
        name='GODATA 평일 자동수집 (17:30)',
        replace_existing=True,
        misfire_grace_time=600,   # 10분 이내 늦게 실행돼도 허용
    )

    # 토요일 20:30
    scheduler.add_job(
        _run_sync,
        trigger=CronTrigger(day_of_week='sat', hour=20, minute=30, timezone='Asia/Seoul'),
        id='godata_saturday',
        name='GODATA 토요일 자동수집 (20:30)',
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info('GODATA 자동수집 스케줄러 시작 — 평일 17:30 / 토요일 20:30')
    return scheduler


def _run_sync():
    """스케줄러가 호출하는 실제 동기화 함수."""
    from reports.godata_scraper import sync_godata_to_db
    logger.info('GODATA 자동수집 실행')
    sync_godata_to_db()
