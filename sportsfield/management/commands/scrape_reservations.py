import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime

from django.utils import timezone as tz

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from sportsfield.models import Reservation

LOGIN_URL = 'https://yongsanparkstory.kr/_wp/admin/loginout/loginout_main.php'
CALENDAR_URL = 'https://yongsanparkstory.kr/_wp/admin/sub/reservation_list_c.html'
DETAIL_URL = 'https://yongsanparkstory.kr/_wp/admin/sub/reservation_list.html'
LOGIN_ID = 'admin'
LOGIN_PW = '1234'

FIELD_MAP = {
    '6': 'baseball',
    '4': 'soccer',
    '15': 'tennis_grass',
    '14': 'tennis_hard',
}


def get_session():
    session = requests.Session()
    session.post(LOGIN_URL, data={'type': 'chk', 'adId': LOGIN_ID, 'adPw': LOGIN_PW}, timeout=15)
    return session


def scrape_month(session, s_item, year, month):
    url = f'{CALENDAR_URL}?pageDate={year}-{month}&sItem={s_item}'
    resp = session.get(url, timeout=15)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')

    table = soup.find('table', class_='wp_reserve_calendar')
    if not table:
        return []

    results = []
    tbody = table.find('tbody')
    if not tbody:
        return []

    for td in tbody.find_all('td'):
        day_wrap = td.find(class_='wp_day_wrap')
        if not day_wrap:
            continue
        day_text = day_wrap.get_text(strip=True)
        if not day_text.isdigit():
            continue
        day_num = int(day_text)
        res_date = date(year, month, day_num)

        for li in td.find_all('li'):
            a_tag = li.find('a')
            if not a_tag:
                continue
            text = a_tag.get_text(strip=True)
            m = re.match(r'(\d{2}:\d{2})~(\d{2}:\d{2})\s+(.+?)\s+\((.+?)\)', text)
            if not m:
                continue
            time_start = datetime.strptime(m.group(1), '%H:%M').time()
            time_end = datetime.strptime(m.group(2), '%H:%M').time()
            applicant = m.group(3).strip()
            status_text = m.group(4)
            status = 'confirmed' if status_text == '예약완료' else 'cancelled'

            href = a_tag.get('href', '')
            rv_match = re.search(r'rvNo=(\d+)', href)
            if not rv_match:
                continue
            rv_no = int(rv_match.group(1))

            results.append({
                'field_type': FIELD_MAP[s_item],
                'reservation_date': res_date,
                'time_start': time_start,
                'time_end': time_end,
                'applicant_name': applicant,
                'status': status,
                'rv_no': rv_no,
            })
    return results


def scrape_detail(session, rv_no):
    url = f'{DETAIL_URL}?type=input&dmlMode=update&rvNo={rv_no}'
    resp = session.get(url, timeout=15)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')

    data = {}
    for table in soup.find_all('table', class_='wp_row'):
        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text(strip=True)
                val = td.get_text(strip=True)
                data[key] = val

    # 예약상태는 select에서 선택된 option
    rv_status = ''
    status_sel = soup.find('select', id='rvStatus')
    if status_sel:
        sel_opt = status_sel.find('option', selected=True)
        if sel_opt:
            rv_status = sel_opt.get_text(strip=True)

    # 예약 신청일자 파싱
    applied_at = None
    applied_str = data.get('예약 신청일자', '')
    if applied_str:
        try:
            naive = datetime.strptime(applied_str, '%Y-%m-%d %H:%M:%S')
            applied_at = tz.make_aware(naive)
        except ValueError:
            pass

    def to_int(s):
        s = re.sub(r'[^\d]', '', s or '')
        return int(s) if s else None

    return {
        'reservation_number': data.get('예약번호', ''),
        'birth_date': data.get('예약자 생년월일', ''),
        'phone': data.get('예약자 연락처', ''),
        'email': data.get('예약자 이메일', ''),
        'organization': data.get('소속', ''),
        'total_users': to_int(data.get('예약인원(명)', '')),
        'scoreboard': data.get('전광판 사용 여부', ''),
        'applied_at': applied_at,
        'adult_count': to_int(data.get('만13세~성인 인원', '')),
        'child_count': to_int(data.get('만0세~만12세 인원', '')),
        'rv_status': rv_status,
    }


class Command(BaseCommand):
    help = '예약 현황 사이트에서 데이터를 크롤링하여 DB에 저장합니다.'

    def handle(self, *args, **options):
        start_time = time.time()
        today = date.today()
        months = [(today.year, today.month)]
        if today.month == 12:
            months.append((today.year + 1, 1))
        else:
            months.append((today.year, today.month + 1))

        self.stdout.write('로그인 중...')
        session = get_session()

        created = updated = 0
        all_rv_nos = []

        # 1단계: 달력 병렬 수집 (4구장 × 2개월 = 8 요청 동시)
        tasks = [(s_item, year, month) for s_item in FIELD_MAP for year, month in months]
        self.stdout.write(f'달력 수집 중 ({len(tasks)}페이지 병렬)...')

        calendar_results = {}
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {
                executor.submit(scrape_month, session, s, y, m): (s, y, m)
                for s, y, m in tasks
            }
            for future in as_completed(futures):
                s_item, year, month = futures[future]
                try:
                    calendar_results[(s_item, year, month)] = future.result()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'  달력 수집 실패 [{FIELD_MAP[s_item]}] {year}-{month:02d}: {e}'
                    ))

        for records in calendar_results.values():
            for r in records:
                obj, was_created = Reservation.objects.update_or_create(
                    rv_no=r['rv_no'],
                    defaults=r,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                all_rv_nos.append(r['rv_no'])

        # 2단계: 상세 정보 병렬 수집 (미수집 건만)
        needs_detail = list(
            Reservation.objects.filter(rv_no__in=all_rv_nos, phone='')
            .values_list('rv_no', flat=True)
        )
        self.stdout.write(f'상세 정보 수집 중 ({len(needs_detail)}건 병렬)...')

        detail_ok = detail_fail = 0
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {
                executor.submit(scrape_detail, session, rv_no): rv_no
                for rv_no in needs_detail
            }
            for future in as_completed(futures):
                rv_no = futures[future]
                try:
                    detail = future.result()
                    Reservation.objects.filter(rv_no=rv_no).update(**detail)
                    detail_ok += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  rvNo={rv_no} 상세 수집 실패: {e}'))
                    detail_fail += 1

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f'완료: 신규 {created}건, 업데이트 {updated}건, 상세 {detail_ok}건'
            + (f' (실패 {detail_fail}건)' if detail_fail else '')
            + f' (소요 시간: {elapsed:.1f}초)'
        ))
