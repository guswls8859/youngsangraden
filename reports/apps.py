import os
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

        # Django runserver의 auto-reloader는 프로세스를 2번 실행한다.
        # RUN_MAIN=true 인 실제 워커 프로세스에서만 스케줄러를 시작한다.
        # 프로덕션(gunicorn 등)에서는 RUN_MAIN이 설정되지 않으므로 항상 시작.
        is_runserver = len(sys.argv) > 1 and sys.argv[1] == 'runserver'
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        from reports.scheduler import start
        start()
