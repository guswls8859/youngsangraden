from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .forms import VehicleForm
from .models import Vehicle, ParkingLog


class ParkingAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.can_access_parking:
            return redirect('main_menu')
        return super().dispatch(request, *args, **kwargs)


class VehicleListView(ParkingAccessMixin, ListView):
    model = Vehicle
    template_name = 'parking/vehicle_list.html'
    context_object_name = 'vehicles'

    def get_queryset(self):
        qs = Vehicle.objects.all()
        filter_type = self.request.GET.get('filter', 'active')
        today = timezone.localdate()
        if filter_type == 'active':
            qs = qs.filter(start_date__lte=today, end_date__gte=today)
        elif filter_type == 'expired':
            qs = qs.filter(end_date__lt=today)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        ctx['today'] = today
        ctx['filter'] = self.request.GET.get('filter', 'active')
        today_logs = ParkingLog.objects.filter(date=today).select_related('vehicle')
        ctx['today_logs'] = {log.vehicle_id: log for log in today_logs}
        return ctx


class VehicleDetailView(ParkingAccessMixin, DetailView):
    model = Vehicle
    template_name = 'parking/vehicle_detail.html'
    context_object_name = 'vehicle'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['logs'] = self.object.logs.select_related('updated_by').order_by('-date')
        ctx['today'] = timezone.localdate()
        ctx['today_log'] = self.object.today_log()
        return ctx


class VehicleCreateView(ParkingAccessMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'parking/vehicle_form.html'
    success_url = reverse_lazy('parking:list')

    def form_valid(self, form):
        form.instance.registered_by = self.request.user
        return super().form_valid(form)


class VehicleUpdateView(ParkingAccessMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'parking/vehicle_form.html'

    def get_success_url(self):
        return reverse_lazy('parking:detail', kwargs={'pk': self.object.pk})


@login_required
def parking_action(request, pk, action):
    if not request.user.can_access_parking:
        return redirect('main_menu')

    vehicle = get_object_or_404(Vehicle, pk=pk)
    today = timezone.localdate()
    now = timezone.now()

    log, _ = ParkingLog.objects.get_or_create(
        vehicle=vehicle, date=today,
        defaults={'status': 'waiting'}
    )

    if action == 'enter' and log.status == 'waiting':
        log.status = 'entered'
        log.entered_at = now
        log.updated_by = request.user
        log.save()
    elif action == 'exit' and log.status == 'entered':
        log.status = 'exited'
        log.exited_at = now
        log.updated_by = request.user
        log.save()
    elif action == 'reset':
        log.status = 'waiting'
        log.entered_at = None
        log.exited_at = None
        log.updated_by = request.user
        log.save()

    return redirect('parking:detail', pk=pk)


@login_required
def vehicle_delete(request, pk):
    if not request.user.can_access_parking:
        return redirect('main_menu')
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        vehicle.delete()
        return redirect('parking:list')
    return redirect('parking:detail', pk=pk)
