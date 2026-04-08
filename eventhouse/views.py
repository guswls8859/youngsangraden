import calendar
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from .models import EventhouseRecord


class EventhouseAccessMixin(LoginRequiredMixin):
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


class EventhouseMainView(EventhouseAccessMixin, TemplateView):
    template_name = 'eventhouse/main.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year, month = _get_year_month(self.request)
        prev_year, prev_month, next_year, next_month = _prev_next(year, month)

        records = EventhouseRecord.objects.filter(
            record_date__year=year,
            record_date__month=month,
        )

        cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
        day_map = {}
        for r in records:
            d = r.record_date.day
            day_map.setdefault(d, []).append({
                'pk': r.pk,
                'space_name': r.space_name,
                'title': r.title,
                'time_start': r.time_start,
                'time_end': r.time_end,
            })
        for d in day_map:
            day_map[d].sort(key=lambda x: (x['time_start'] or date.min, x['space_name']))

        ctx.update({
            'year': year,
            'month': month,
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,
            'cal': cal,
            'day_map': day_map,
            'today': date.today(),
        })
        return ctx


class RecordCreateView(EventhouseAccessMixin, View):
    def post(self, request):
        space_name = request.POST.get('space_name', '').strip()
        title = request.POST.get('title', '').strip()
        record_date = request.POST.get('record_date', '')
        time_start = request.POST.get('time_start', '').strip() or None
        time_end = request.POST.get('time_end', '').strip() or None
        memo = request.POST.get('memo', '').strip()

        if not all([space_name, title, record_date]):
            return JsonResponse({'ok': False, 'message': '필수 항목을 입력해주세요.'}, status=400)

        EventhouseRecord.objects.create(
            space_name=space_name,
            title=title,
            record_date=record_date,
            time_start=time_start,
            time_end=time_end,
            memo=memo,
            author=request.user,
        )
        return JsonResponse({'ok': True})


class RecordDetailView(EventhouseAccessMixin, View):
    def get(self, request, pk):
        r = get_object_or_404(EventhouseRecord, pk=pk)

        def fmt(t):
            return t.strftime('%H:%M') if t else ''

        return JsonResponse({
            'ok': True,
            'pk': r.pk,
            'space_name': r.space_name,
            'title': r.title,
            'date': r.record_date.strftime('%Y년 %m월 %d일'),
            'time': f'{fmt(r.time_start)}~{fmt(r.time_end)}' if r.time_start else '-',
            'memo': r.memo,
            'author': r.author.get_full_name() or r.author.username,
        })


class RecordDeleteView(EventhouseAccessMixin, View):
    def post(self, request, pk):
        record = get_object_or_404(EventhouseRecord, pk=pk)
        record.delete()
        return JsonResponse({'ok': True})
