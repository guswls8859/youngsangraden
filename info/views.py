import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView

from .forms import InfoReportForm
from .models import InfoReport, InfoReportItem


class InfoAccessMixin(LoginRequiredMixin):
    """안내센터 또는 운영사무국 소속만 접근 가능"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_info:
            return redirect('main_menu')
        return super().dispatch(request, *args, **kwargs)


class InfoWriteMixin(LoginRequiredMixin):
    """안내센터 소속 직원만 작성 가능"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.organization != 'info':
            return redirect('info:list')
        return super().dispatch(request, *args, **kwargs)


def save_items(request, report):
    """POST 데이터에서 섹션별 항목을 파싱해 저장한다."""
    report.items.all().delete()
    for section in ('info', 'shuttle', 'patrol'):
        count = int(request.POST.get(f'{section}_count', 0))
        for i in range(count):
            content = request.POST.get(f'{section}_{i}_content', '').strip()
            if content:
                InfoReportItem.objects.create(
                    report=report,
                    section=section,
                    content=content,
                    order=i,
                )


class InfoReportListView(InfoAccessMixin, ListView):
    model = InfoReport
    template_name = 'info/list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        if self.request.user.organization == 'info':
            return InfoReport.objects.filter(author=self.request.user).select_related('author')
        return InfoReport.objects.select_related('author').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['today'] = timezone.localdate()
        ctx['can_write'] = self.request.user.organization == 'info'
        ctx['today_report'] = InfoReport.objects.filter(
            author=self.request.user,
            report_date=timezone.localdate()
        ).first() if ctx['can_write'] else None
        return ctx


class InfoReportDetailView(InfoAccessMixin, DetailView):
    model = InfoReport
    template_name = 'info/detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(self.object.items.all())
        ctx['info_items']    = [t for t in items if t.section == 'info']
        ctx['shuttle_items'] = [t for t in items if t.section == 'shuttle']
        ctx['patrol_items']  = [t for t in items if t.section == 'patrol']
        ctx['can_edit'] = (
            self.request.user.organization == 'info' and
            self.object.author == self.request.user
        )
        return ctx


class InfoReportCreateView(InfoWriteMixin, CreateView):
    model = InfoReport
    form_class = InfoReportForm
    template_name = 'info/form.html'
    success_url = reverse_lazy('info:list')

    def get_initial(self):
        return {'report_date': timezone.localdate()}

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.status = 'submitted'
        report = form.save()
        save_items(self.request, report)
        return redirect(self.success_url)


class InfoReportUpdateView(InfoWriteMixin, UpdateView):
    model = InfoReport
    form_class = InfoReportForm
    template_name = 'info/form.html'

    def get_queryset(self):
        return InfoReport.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(self.object.items.all())
        ctx['existing_info']    = [{'content': t.content} for t in items if t.section == 'info']
        ctx['existing_shuttle'] = [{'content': t.content} for t in items if t.section == 'shuttle']
        ctx['existing_patrol']  = [{'content': t.content} for t in items if t.section == 'patrol']
        return ctx

    def form_valid(self, form):
        report = form.save()
        save_items(self.request, report)
        return redirect(reverse_lazy('info:detail', kwargs={'pk': report.pk}))


class InfoReportDeleteView(InfoWriteMixin, DeleteView):
    model = InfoReport
    success_url = reverse_lazy('info:list')

    def get_queryset(self):
        return InfoReport.objects.filter(author=self.request.user)

class InfoDashboardView(InfoAccessMixin, TemplateView):
    """날짜별 전체 제출 현황"""
    template_name = 'info/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        date_str = self.request.GET.get('date')
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except (TypeError, ValueError):
            target_date = timezone.localdate()

        reports = (
            InfoReport.objects
            .filter(report_date=target_date, status='submitted')
            .select_related('author')
            .prefetch_related('items')
            .order_by('author__last_name', 'author__username')
        )

        ctx['target_date'] = target_date
        ctx['prev_date'] = target_date - datetime.timedelta(days=1)
        ctx['next_date'] = target_date + datetime.timedelta(days=1)
        ctx['reports'] = reports
        return ctx
