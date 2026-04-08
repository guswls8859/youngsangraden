import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from .forms import KumnareReportForm, EoulrimReportForm, JamjamReportForm
from .models import KumnareReport, KumnareRentalItem, EoulrimReport, EoulrimNewMenuItem, JamjamReport, JamjamNewMenuItem


# ── 접근 제어 Mixin ──────────────────────────────────────────────

class FacilitiesAccessMixin(LoginRequiredMixin):
    """편익시설 전체 (3개 중 하나 이상) 또는 운영사무국"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_facilities:
            return redirect('main_menu')
        return super().dispatch(request, *args, **kwargs)


class KumnareAccessMixin(LoginRequiredMixin):
    """꿈나래마켓 또는 운영사무국 - 읽기 가능"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_kumnare:
            return redirect('facilities:menu')
        return super().dispatch(request, *args, **kwargs)


class KumnareWriteMixin(LoginRequiredMixin):
    """꿈나래마켓 소속 직원만 작성 가능"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.organization != 'dreammarket':
            return redirect('facilities:kumnare')
        return super().dispatch(request, *args, **kwargs)


class EoulrimAccessMixin(LoginRequiredMixin):
    """카페 어울림 또는 운영사무국"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_eoulrim:
            return redirect('facilities:menu')
        return super().dispatch(request, *args, **kwargs)


class JamjamAccessMixin(LoginRequiredMixin):
    """잼잼 카페 또는 운영사무국"""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_jamjam:
            return redirect('facilities:menu')
        return super().dispatch(request, *args, **kwargs)


# ── 편익시설 메뉴 ─────────────────────────────────────────────────

class FacilitiesMenuView(FacilitiesAccessMixin, TemplateView):
    template_name = 'facilities/menu.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['can_access_kumnare'] = user.can_access_kumnare
        ctx['can_access_eoulrim'] = user.can_access_eoulrim
        ctx['can_access_jamjam']  = user.can_access_jamjam
        return ctx


# ── 꿈나래마켓 ────────────────────────────────────────────────────

FIXED_RENTAL_ITEMS = ['테이블', '캠핑의자', '돗자리', '담요']


def _save_rental_items(request, report):
    """POST 데이터에서 렌탈 품목(고정 4개 + 추가)을 파싱해 저장한다."""
    report.rental_items.all().delete()
    order = 0
    # 고정 품목 4개 (항상 저장)
    for name in FIXED_RENTAL_ITEMS:
        key = f'fixed_{name}_count'
        cnt = request.POST.get(key, '0').strip()
        KumnareRentalItem.objects.create(
            report=report,
            item_name=name,
            count=int(cnt) if cnt.isdigit() else 0,
            order=order,
        )
        order += 1
    # 추가 품목
    extra_count = int(request.POST.get('extra_item_count', 0))
    for i in range(extra_count):
        name = request.POST.get(f'extra_item_{i}_name', '').strip()
        cnt  = request.POST.get(f'extra_item_{i}_count', '0').strip()
        if name:
            KumnareRentalItem.objects.create(
                report=report,
                item_name=name,
                count=int(cnt) if cnt.isdigit() else 0,
                order=order,
            )
            order += 1


class KumnareReportListView(KumnareAccessMixin, ListView):
    model = KumnareReport
    template_name = 'facilities/kumnare_list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        return KumnareReport.objects.select_related('author').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_write'] = self.request.user.organization == 'dreammarket'
        ctx['today'] = timezone.localdate()
        return ctx


class KumnareReportDetailView(KumnareAccessMixin, DetailView):
    model = KumnareReport
    template_name = 'facilities/kumnare_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['rental_items'] = self.object.rental_items.all()
        ctx['can_edit'] = self.request.user.organization == 'dreammarket'
        return ctx


class KumnareReportCreateView(KumnareWriteMixin, CreateView):
    model = KumnareReport
    form_class = KumnareReportForm
    template_name = 'facilities/kumnare_form.html'
    success_url = reverse_lazy('facilities:kumnare')

    def get_initial(self):
        return {'report_date': timezone.localdate()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fixed_item_names'] = FIXED_RENTAL_ITEMS
        ctx['fixed_names_json'] = json.dumps(FIXED_RENTAL_ITEMS, ensure_ascii=False)
        ctx['fixed_counts_json'] = '{}'
        ctx['extra_items_json'] = '[]'
        return ctx

    def form_valid(self, form):
        form.instance.author = self.request.user
        report = form.save()
        _save_rental_items(self.request, report)
        return redirect(self.success_url)


class KumnareReportUpdateView(KumnareWriteMixin, UpdateView):
    model = KumnareReport
    form_class = KumnareReportForm
    template_name = 'facilities/kumnare_form.html'

    def get_queryset(self):
        return KumnareReport.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = list(self.object.rental_items.all())
        fixed_counts = {name: 0 for name in FIXED_RENTAL_ITEMS}
        extra_items = []
        for item in items:
            if item.item_name in fixed_counts:
                fixed_counts[item.item_name] = item.count
            else:
                extra_items.append({'item_name': item.item_name, 'count': item.count})
        ctx['fixed_item_names'] = FIXED_RENTAL_ITEMS
        ctx['fixed_names_json'] = json.dumps(FIXED_RENTAL_ITEMS, ensure_ascii=False)
        ctx['fixed_counts_json'] = json.dumps(fixed_counts, ensure_ascii=False)
        ctx['extra_items_json'] = json.dumps(extra_items, ensure_ascii=False)
        return ctx

    def form_valid(self, form):
        report = form.save()
        _save_rental_items(self.request, report)
        return redirect(reverse_lazy('facilities:kumnare_detail', kwargs={'pk': report.pk}))


class KumnareReportDeleteView(KumnareWriteMixin, DeleteView):
    model = KumnareReport
    success_url = reverse_lazy('facilities:kumnare')

    def get_queryset(self):
        return KumnareReport.objects.filter(author=self.request.user)


# ── 카페 어울림 ───────────────────────────────────────────────────

def _save_new_menu_items(request, report):
    """POST 데이터에서 신메뉴 항목(동적)을 파싱해 저장한다."""
    report.new_menu_items.all().delete()
    item_count = int(request.POST.get('menu_item_count', 0))
    for i in range(item_count):
        name = request.POST.get(f'menu_{i}_name', '').strip()
        cnt  = request.POST.get(f'menu_{i}_count', '0').strip()
        if name:
            EoulrimNewMenuItem.objects.create(
                report=report,
                name=name,
                count=int(cnt) if cnt.isdigit() else 0,
                order=i,
            )


class EoulrimReportListView(EoulrimAccessMixin, ListView):
    model = EoulrimReport
    template_name = 'facilities/eoulrim_list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        return EoulrimReport.objects.select_related('author').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_write'] = self.request.user.organization == 'eulrimcafe'
        ctx['today'] = timezone.localdate()
        return ctx


class EoulrimReportDetailView(EoulrimAccessMixin, DetailView):
    model = EoulrimReport
    template_name = 'facilities/eoulrim_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['new_menu_items'] = self.object.new_menu_items.all()
        ctx['can_edit'] = self.request.user.organization == 'eulrimcafe'
        # 당월 총 순매출
        d = self.object.report_date
        from django.db.models import Sum
        monthly = EoulrimReport.objects.filter(
            report_date__year=d.year, report_date__month=d.month
        ).aggregate(total=Sum('daily_net_sales'))
        ctx['monthly_total'] = monthly['total'] or 0
        return ctx


class EoulrimWriteMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.organization != 'eulrimcafe':
            return redirect('facilities:eoulrim')
        return super().dispatch(request, *args, **kwargs)


class EoulrimReportCreateView(EoulrimWriteMixin, CreateView):
    model = EoulrimReport
    form_class = EoulrimReportForm
    template_name = 'facilities/eoulrim_form.html'
    success_url = reverse_lazy('facilities:eoulrim')

    def get_initial(self):
        return {'report_date': timezone.localdate()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['menu_items_json'] = '[]'
        return ctx

    def form_valid(self, form):
        form.instance.author = self.request.user
        report = form.save()
        _save_new_menu_items(self.request, report)
        return redirect(self.success_url)


class EoulrimReportUpdateView(EoulrimWriteMixin, UpdateView):
    model = EoulrimReport
    form_class = EoulrimReportForm
    template_name = 'facilities/eoulrim_form.html'

    def get_queryset(self):
        return EoulrimReport.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import json
        items = list(self.object.new_menu_items.values('name', 'count'))
        ctx['menu_items_json'] = json.dumps(items, ensure_ascii=False)
        return ctx

    def form_valid(self, form):
        report = form.save()
        _save_new_menu_items(self.request, report)
        return redirect(reverse_lazy('facilities:eoulrim_detail', kwargs={'pk': report.pk}))


class EoulrimReportDeleteView(EoulrimWriteMixin, DeleteView):
    model = EoulrimReport
    success_url = reverse_lazy('facilities:eoulrim')

    def get_queryset(self):
        return EoulrimReport.objects.filter(author=self.request.user)


# ── 잼잼카페 ─────────────────────────────────────────────────────────

def _save_jamjam_menu_items(request, report):
    report.new_menu_items.all().delete()
    item_count = int(request.POST.get('menu_item_count', 0))
    for i in range(item_count):
        name = request.POST.get(f'menu_{i}_name', '').strip()
        cnt  = request.POST.get(f'menu_{i}_count', '0').strip()
        if name:
            JamjamNewMenuItem.objects.create(
                report=report,
                name=name,
                count=int(cnt) if cnt.isdigit() else 0,
                order=i,
            )


class JamjamReportListView(JamjamAccessMixin, ListView):
    model = JamjamReport
    template_name = 'facilities/jamjam_list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        return JamjamReport.objects.select_related('author').all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_write'] = self.request.user.organization == 'jemjemcafe'
        ctx['today'] = timezone.localdate()
        return ctx


class JamjamReportDetailView(JamjamAccessMixin, DetailView):
    model = JamjamReport
    template_name = 'facilities/jamjam_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['new_menu_items'] = self.object.new_menu_items.all()
        ctx['can_edit'] = self.request.user.organization == 'jemjemcafe'
        d = self.object.report_date
        from django.db.models import Sum
        monthly = JamjamReport.objects.filter(
            report_date__year=d.year, report_date__month=d.month
        ).aggregate(total=Sum('daily_net_sales'))
        ctx['monthly_total'] = monthly['total'] or 0
        return ctx


class JamjamWriteMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.organization != 'jemjemcafe':
            return redirect('facilities:jamjam')
        return super().dispatch(request, *args, **kwargs)


class JamjamReportCreateView(JamjamWriteMixin, CreateView):
    model = JamjamReport
    form_class = JamjamReportForm
    template_name = 'facilities/jamjam_form.html'
    success_url = reverse_lazy('facilities:jamjam')

    def get_initial(self):
        return {'report_date': timezone.localdate()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['menu_items_json'] = '[]'
        return ctx

    def form_valid(self, form):
        form.instance.author = self.request.user
        report = form.save()
        _save_jamjam_menu_items(self.request, report)
        return redirect(self.success_url)


class JamjamReportUpdateView(JamjamWriteMixin, UpdateView):
    model = JamjamReport
    form_class = JamjamReportForm
    template_name = 'facilities/jamjam_form.html'

    def get_queryset(self):
        return JamjamReport.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        import json
        items = list(self.object.new_menu_items.values('name', 'count'))
        ctx['menu_items_json'] = json.dumps(items, ensure_ascii=False)
        return ctx

    def form_valid(self, form):
        report = form.save()
        _save_jamjam_menu_items(self.request, report)
        return redirect(reverse_lazy('facilities:jamjam_detail', kwargs={'pk': report.pk}))


class JamjamReportDeleteView(JamjamWriteMixin, DeleteView):
    model = JamjamReport
    success_url = reverse_lazy('facilities:jamjam')

    def get_queryset(self):
        return JamjamReport.objects.filter(author=self.request.user)
