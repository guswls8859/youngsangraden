import calendar
import json
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.management import call_command
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from .models import FIELD_CHOICES, Reservation, SportsfieldEntry

TIME_SLOTS = {
    'soccer': [
        ('10:00', '12:00', '1타임 (10:00~12:00)'),
        ('13:00', '15:00', '2타임 (13:00~15:00)'),
        ('15:30', '17:30', '3타임 (15:30~17:30)'),
    ],
    'baseball': [
        ('10:00', '14:00', '1타임 (10:00~14:00)'),
        ('14:00', '18:00', '2타임 (14:00~18:00)'),
    ],
    'tennis_grass': [
        ('10:00', '12:00', '1타임 (10:00~12:00)'),
        ('13:00', '15:00', '2타임 (13:00~15:00)'),
        ('15:30', '17:30', '3타임 (15:30~17:30)'),
    ],
    'tennis_hard': [
        ('10:00', '12:00', '1타임 (10:00~12:00)'),
        ('13:00', '15:00', '2타임 (13:00~15:00)'),
        ('15:30', '17:30', '3타임 (15:30~17:30)'),
    ],
}


class SportsfieldAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_sportsfield:
            return redirect('main_menu')
        return super().dispatch(request, *args, **kwargs)


def _get_year_month(request):
    try:
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))
        if month < 1 or month > 12:
            raise ValueError
    except (ValueError, TypeError):
        year = date.today().year
        month = date.today().month
    return year, month


def _prev_next(year, month):
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    return prev_year, prev_month, next_year, next_month


def _build_calendar(year, month, reservations, entries):
    cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    day_map = {}

    for r in reservations:
        d = r.reservation_date.day
        day_map.setdefault(d, []).append({
            'category': 'normal',
            'time_start': r.time_start,
            'time_end': r.time_end,
            'title': r.applicant_name,
            'is_manual': False,
            'rv_no': r.rv_no,
            'entry_id': None,
            'actual_adult': r.actual_adult_count,
            'actual_child': r.actual_child_count,
            'is_noshow': r.is_noshow,
        })

    for e in entries:
        d = e.entry_date.day
        reserved = None
        if e.reserved_adult_count is not None or e.reserved_child_count is not None:
            reserved = (e.reserved_adult_count or 0) + (e.reserved_child_count or 0)
        day_map.setdefault(d, []).append({
            'category': e.category,
            'time_start': e.time_start,
            'time_end': e.time_end,
            'title': e.title,
            'is_manual': True,
            'rv_no': None,
            'entry_id': e.pk,
            'reserved_count': reserved,
            'actual_adult': e.actual_adult_count,
            'actual_child': e.actual_child_count,
            'is_noshow': e.is_noshow,
        })

    for d in day_map:
        day_map[d].sort(key=lambda x: (x['time_start'] or date.min, x['title']))

    return cal, day_map


class SportsfieldMainView(SportsfieldAccessMixin, TemplateView):
    template_name = 'sportsfield/main.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year, month = _get_year_month(self.request)
        prev_year, prev_month, next_year, next_month = _prev_next(year, month)

        reservations = Reservation.objects.filter(
            reservation_date__year=year,
            reservation_date__month=month,
            status='confirmed',
        )
        entries = SportsfieldEntry.objects.filter(
            entry_date__year=year,
            entry_date__month=month,
        )

        field_calendars = {}
        for field_key, field_label in FIELD_CHOICES:
            cal, day_map = _build_calendar(
                year, month,
                reservations.filter(field_type=field_key),
                entries.filter(field_type=field_key),
            )
            field_calendars[field_key] = {
                'label': field_label,
                'cal': cal,
                'day_map': day_map,
            }

        last_scraped = Reservation.objects.order_by('-scraped_at').values_list('scraped_at', flat=True).first()

        ctx.update({
            'year': year,
            'month': month,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'fields': FIELD_CHOICES,
            'field_calendars': field_calendars,
            'today': date.today(),
            'time_slots_json': json.dumps(TIME_SLOTS),
            'last_scraped': last_scraped,
        })
        return ctx


class SportsfieldUsageView(SportsfieldAccessMixin, TemplateView):
    template_name = 'sportsfield/usage.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year, month = _get_year_month(self.request)
        prev_year, prev_month, next_year, next_month = _prev_next(year, month)

        reservations = Reservation.objects.filter(
            reservation_date__year=year,
            reservation_date__month=month,
            status='confirmed',
        )
        entries = SportsfieldEntry.objects.filter(
            entry_date__year=year,
            entry_date__month=month,
        )

        field_calendars = {}
        for field_key, field_label in FIELD_CHOICES:
            cal, day_map = _build_calendar(
                year, month,
                reservations.filter(field_type=field_key),
                entries.filter(field_type=field_key),
            )
            field_calendars[field_key] = {
                'label': field_label,
                'cal': cal,
                'day_map': day_map,
            }

        ctx.update({
            'year': year,
            'month': month,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'fields': FIELD_CHOICES,
            'field_calendars': field_calendars,
            'today': date.today(),
        })
        return ctx


class SportsfieldCancelView(SportsfieldAccessMixin, TemplateView):
    template_name = 'sportsfield/cancel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year, month = _get_year_month(self.request)
        prev_year, prev_month, next_year, next_month = _prev_next(year, month)

        cancelled = Reservation.objects.filter(
            reservation_date__year=year,
            reservation_date__month=month,
            status='cancelled',
        )

        field_calendars = {}
        for field_key, field_label in FIELD_CHOICES:
            cal, day_map = _build_calendar(
                year, month,
                cancelled.filter(field_type=field_key),
                SportsfieldEntry.objects.none(),
            )
            field_calendars[field_key] = {
                'label': field_label,
                'cal': cal,
                'day_map': day_map,
                'count': cancelled.filter(field_type=field_key).count(),
            }

        ctx.update({
            'year': year,
            'month': month,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'fields': FIELD_CHOICES,
            'field_calendars': field_calendars,
            'today': date.today(),
            'total_count': cancelled.count(),
        })
        return ctx


class ScrapeRefreshView(SportsfieldAccessMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            call_command('scrape_reservations')
            last = Reservation.objects.order_by('-scraped_at').values_list('scraped_at', flat=True).first()
            scraped_str = last.strftime('%Y-%m-%d %H:%M') if last else ''
            return JsonResponse({'ok': True, 'scraped_at': scraped_str})
        except Exception as e:
            return JsonResponse({'ok': False, 'message': str(e)}, status=500)


class ReservationDetailView(SportsfieldAccessMixin, View):
    def get(self, request, rv_no):
        r = get_object_or_404(Reservation, rv_no=rv_no)

        def fmt_time(t):
            return t.strftime('%H:%M') if t else ''

        return JsonResponse({
            'ok': True,
            'type': 'normal',
            'field': r.get_field_type_display(),
            'date': r.reservation_date.strftime('%Y년 %m월 %d일'),
            'time': f'{fmt_time(r.time_start)}~{fmt_time(r.time_end)}',
            'name': r.applicant_name,
            'phone': r.phone,
            'birth_date': r.birth_date,
            'email': r.email,
            'organization': r.organization,
            'total_users': r.total_users,
            'scoreboard': r.scoreboard,
            'adult_count': r.adult_count,
            'child_count': r.child_count,
            'applied_at': r.applied_at.strftime('%Y-%m-%d %H:%M') if r.applied_at else '',
            'rv_status': r.rv_status,
            'reservation_number': r.reservation_number,
            'actual_adult_count': r.actual_adult_count,
            'actual_child_count': r.actual_child_count,
            'is_noshow': r.is_noshow,
            'usage_memo': r.usage_memo,
        })


class EntryDetailView(SportsfieldAccessMixin, View):
    def get(self, request, pk):
        e = get_object_or_404(SportsfieldEntry, pk=pk)

        def fmt_time(t):
            return t.strftime('%H:%M') if t else ''

        return JsonResponse({
            'ok': True,
            'type': 'manual',
            'field': e.get_field_type_display(),
            'date': e.entry_date.strftime('%Y년 %m월 %d일'),
            'time': f'{fmt_time(e.time_start)}~{fmt_time(e.time_end)}' if e.time_start else '',
            'title': e.title,
            'category': e.get_category_display(),
            'author': e.author.get_full_name() or e.author.username,
            'reserved_adult_count': e.reserved_adult_count,
            'reserved_child_count': e.reserved_child_count,
            'actual_adult_count': e.actual_adult_count,
            'actual_child_count': e.actual_child_count,
            'is_noshow': e.is_noshow,
            'usage_memo': e.usage_memo,
        })


class EntryCreateView(SportsfieldAccessMixin, View):
    def post(self, request, *args, **kwargs):
        field_type = request.POST.get('field_type')
        entry_date = request.POST.get('entry_date')
        time_slot = request.POST.get('time_slot', '')
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category')

        valid_fields = [f[0] for f in FIELD_CHOICES]
        valid_cats = ['normal', 'quarter', 'event', 'other']

        if not all([field_type, entry_date, title, category, time_slot]):
            return JsonResponse({'ok': False, 'message': '필수 항목을 모두 입력해주세요.'}, status=400)
        if field_type not in valid_fields or category not in valid_cats:
            return JsonResponse({'ok': False, 'message': '잘못된 값입니다.'}, status=400)

        try:
            time_start_str, time_end_str = time_slot.split('|')
        except ValueError:
            return JsonResponse({'ok': False, 'message': '타임 슬롯 형식이 잘못되었습니다.'}, status=400)

        valid_slots = [(s, e) for s, e, _ in TIME_SLOTS.get(field_type, [])]
        if (time_start_str, time_end_str) not in valid_slots:
            return JsonResponse({'ok': False, 'message': '유효하지 않은 타임 슬롯입니다.'}, status=400)

        SportsfieldEntry.objects.create(
            field_type=field_type,
            entry_date=entry_date,
            time_start=time_start_str,
            time_end=time_end_str,
            title=title,
            category=category,
            author=request.user,
            reserved_adult_count=_parse_actual_count(request.POST.get('actual_adult')),
            reserved_child_count=_parse_actual_count(request.POST.get('actual_child')),
        )
        return JsonResponse({'ok': True})


class EntryDeleteView(SportsfieldAccessMixin, View):
    def post(self, request, pk, *args, **kwargs):
        entry = get_object_or_404(SportsfieldEntry, pk=pk)
        entry.delete()
        return JsonResponse({'ok': True})


def _parse_actual_count(val):
    try:
        v = int(val)
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


class ReservationUpdateView(SportsfieldAccessMixin, View):
    def post(self, request, rv_no):
        r = get_object_or_404(Reservation, rv_no=rv_no)
        r.applicant_name = request.POST.get('applicant_name', r.applicant_name).strip() or r.applicant_name
        r.phone          = request.POST.get('phone', '').strip()
        r.birth_date     = request.POST.get('birth_date', '').strip()
        r.email          = request.POST.get('email', '').strip()
        r.organization   = request.POST.get('organization', '').strip()
        r.total_users    = _parse_actual_count(request.POST.get('total_users'))
        r.adult_count    = _parse_actual_count(request.POST.get('adult_count'))
        r.child_count    = _parse_actual_count(request.POST.get('child_count'))
        r.scoreboard     = request.POST.get('scoreboard', '').strip()
        r.rv_status      = request.POST.get('rv_status', '').strip()
        r.save(update_fields=[
            'applicant_name', 'phone', 'birth_date', 'email', 'organization',
            'total_users', 'adult_count', 'child_count', 'scoreboard', 'rv_status',
        ])
        return JsonResponse({'ok': True})


class ReservationUsageUpdateView(SportsfieldAccessMixin, View):
    def post(self, request, rv_no):
        r = get_object_or_404(Reservation, rv_no=rv_no)
        r.actual_adult_count = _parse_actual_count(request.POST.get('actual_adult'))
        r.actual_child_count = _parse_actual_count(request.POST.get('actual_child'))
        r.is_noshow = request.POST.get('is_noshow') == '1'
        r.usage_memo = request.POST.get('usage_memo', '').strip()
        r.save(update_fields=['actual_adult_count', 'actual_child_count', 'is_noshow', 'usage_memo'])
        return JsonResponse({'ok': True})


class EntryUsageUpdateView(SportsfieldAccessMixin, View):
    def post(self, request, pk):
        e = get_object_or_404(SportsfieldEntry, pk=pk)
        e.actual_adult_count = _parse_actual_count(request.POST.get('actual_adult'))
        e.actual_child_count = _parse_actual_count(request.POST.get('actual_child'))
        e.is_noshow = request.POST.get('is_noshow') == '1'
        e.usage_memo = request.POST.get('usage_memo', '').strip()
        e.save(update_fields=['actual_adult_count', 'actual_child_count', 'is_noshow', 'usage_memo'])
        return JsonResponse({'ok': True})
