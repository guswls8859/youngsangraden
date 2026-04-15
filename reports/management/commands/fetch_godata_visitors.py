"""
GODATA 방문자 데이터 수동 수집 명령어

사용법:
    python manage.py fetch_godata_visitors
    python manage.py fetch_godata_visitors --date 2026-04-15
"""
import datetime
from django.core.management.base import BaseCommand, CommandError


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
        from django.utils import timezone
        from reports.godata_scraper import fetch_today_entry_count, sync_godata_to_db

        date_str = options.get('date')
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                raise CommandError(f'날짜 형식 오류: {date_str} (YYYY-MM-DD 형식 필요)')
        else:
            target_date = timezone.localdate()

        self.stdout.write(f'GODATA 수집 시작 (날짜: {target_date})...')

        # 1) 스크래핑
        data = fetch_today_entry_count()
        if data is None:
            self.stdout.write(self.style.ERROR('데이터 수집 실패 — 로그를 확인하세요.'))
            return

        self.stdout.write('')
        self.stdout.write('=== GODATA 수집 결과 ===')
        self.stdout.write(f'  입장 총수   : {data["today_total"]:,} 명')
        self.stdout.write(f'  퇴장 총수   : {data["today_exit"]:,} 명')
        self.stdout.write(f'  주출입구    : {data["main_gate_walk"]:,} 명')
        self.stdout.write(f'  부출입구    : {data["sub_gate_walk"]:,} 명')
        self.stdout.write('')

        # 2) DB 저장 (이미 가져온 data를 그대로 전달 — 재수집 없음)
        success = sync_godata_to_db(target_date=target_date, data=data)

        if not success:
            self.stdout.write(self.style.ERROR('DB 저장 실패 — 로그를 확인하세요.'))
            return

        # 3) DB에 실제로 들어갔는지 확인
        from reports.models import OperationsDailyData
        ops = OperationsDailyData.objects.filter(report_date=target_date).first()
        if ops:
            self.stdout.write('=== DB 저장 확인 ===')
            self.stdout.write(f'  입장 총수   : {ops.today_total:,} 명')
            self.stdout.write(f'  주출입구    : {ops.main_gate_walk:,} 명')
            self.stdout.write(f'  부출입구    : {ops.sub_gate_walk:,} 명')
            self.stdout.write(f'  저장 시각   : {ops.updated_at.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('완료'))
        else:
            self.stdout.write(self.style.ERROR('DB 레코드를 찾을 수 없습니다.'))
