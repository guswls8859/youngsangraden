"""예약정보 조회 API로 스포츠필드 예약을 동기화한다.

(2026-11 이전에는 관리자 페이지 크롤링 방식이었음 — git 이력 참고)
명령 이름은 기존 호출부(새로고침 버튼 등) 호환을 위해 그대로 유지.

허용 IP(34.64.184.142, Cloudtype 서버)에서만 동작한다. 로컬에서는 403.
"""
import datetime as dt
import time

from django.core.management.base import BaseCommand, CommandError

from sportsfield.reservation_api import ReservationAPIError, sync_reservations


class Command(BaseCommand):
    help = '예약정보 조회 API에서 스포츠필드 예약을 가져와 DB에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--start', help='시작일 YYYY-MM-DD (기본: 이번 달 1일)')
        parser.add_argument('--end', help='종료일 YYYY-MM-DD (기본: 다음 달 말일)')

    def handle(self, *args, **options):
        t0 = time.time()
        start = dt.date.fromisoformat(options['start']) if options.get('start') else None
        end = dt.date.fromisoformat(options['end']) if options.get('end') else None
        if (start is None) != (end is None):
            raise CommandError('--start 와 --end 는 함께 지정해야 합니다.')
        try:
            r = sync_reservations(start, end)
        except ReservationAPIError as e:
            raise CommandError(str(e))

        self.stdout.write(self.style.SUCCESS(
            f"완료 ({r['start']}~{r['end']}): 조회 {r['fetched']}건, 신규 {r['created']}건, "
            f"업데이트 {r['updated']}건, API 미조회 취소처리 {r['stale_cancelled']}건 "
            f"(소요 {time.time() - t0:.1f}초)"))
        if r['unmapped']:
            self.stdout.write(self.style.WARNING(f"구장 매핑 안 된 프로그램명: {r['unmapped']}"))
        for err in r['errors']:
            self.stdout.write(self.style.WARNING(f'  파싱 실패 {err}'))
