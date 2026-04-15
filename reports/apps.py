import sys
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    name = 'reports'

    def ready(self):
        # manage.py migrate / makemigrations 등 DB 명령 실행 시엔 스케줄러 시작 안 함
        _skip_cmds = {'migrate', 'makemigrations', 'collectstatic', 'shell'}
        if len(sys.argv) > 1 and sys.argv[1] in _skip_cmds:
            return

        # 테스트 실행 중에도 스케줄러 불필요
        if 'test' in sys.argv:
            return

        from reports.scheduler import start
        start()
