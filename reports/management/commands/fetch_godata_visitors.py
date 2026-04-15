"""
GODATA 방문자 데이터 수동 수집 명령어

사용법:
    python manage.py fetch_godata_visitors
    python manage.py fetch_godata_visitors --date 2026-04-15
"""
import datetime
from django.core.management.base import BaseCommand, CommandError
from reports.godata_scraper import sync_godata_to_db


class Command(BaseCommand):
    help = 'GODATA 피플카운트에서 금일 방문자 수를 가져와 일일보고에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='조회 날짜 (YYYY-MM-DD). 생략 시 오늘.',
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                raise CommandError(f'날짜 형식 오류: {date_str} (YYYY-MM-DD 형식 필요)')
        else:
            target_date = None  # godata_scraper가 오늘 날짜 사용

        self.stdout.write(f'GODATA 동기화 시작 (날짜: {target_date or "오늘"})...')

        success = sync_godata_to_db(target_date)

        if success:
            self.stdout.write(self.style.SUCCESS('GODATA 동기화 완료'))
        else:
            self.stdout.write(self.style.ERROR('GODATA 동기화 실패 — 로그를 확인하세요.'))
