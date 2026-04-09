from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import AdminUserCreateForm, AdminUserEditForm, LoginForm, RegisterForm
from .models import User


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'manager'


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('main_menu')


class UserRegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')


def user_logout(request):
    logout(request)
    return redirect('accounts:login')


# 관리자 패널 뷰

class AdminUserListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = 'accounts/admin/user_list.html'
    context_object_name = 'users'
    ordering = ['username']


class AdminUserCreateView(ManagerRequiredMixin, CreateView):
    model = User
    form_class = AdminUserCreateForm
    template_name = 'accounts/admin/user_form.html'
    success_url = reverse_lazy('accounts:admin_user_list')

    def form_valid(self, form):
        messages.success(self.request, f"사용자 '{form.instance.username}'이(가) 생성되었습니다.")
        return super().form_valid(form)


class AdminUserEditView(ManagerRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserEditForm
    template_name = 'accounts/admin/user_form.html'
    success_url = reverse_lazy('accounts:admin_user_list')

    def form_valid(self, form):
        messages.success(self.request, f"사용자 '{form.instance.username}' 정보가 수정되었습니다.")
        return super().form_valid(form)


@login_required
def set_user_emoji(request):
    """AJAX: 현재 로그인 유저의 이모지 설정"""
    if request.method == 'POST':
        emoji = request.POST.get('emoji', '').strip()
        request.user.emoji = emoji
        request.user.save(update_fields=['emoji'])
        return JsonResponse({'ok': True, 'emoji': emoji})
    return JsonResponse({'error': 'invalid'}, status=400)


@login_required
def admin_user_toggle_active(request, pk):
    if request.user.role != 'manager':
        return redirect('reports:list')
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, '자기 자신의 계정은 비활성화할 수 없습니다.')
        return redirect('accounts:admin_user_list')
    user.is_active = not user.is_active
    user.save()
    status = '활성화' if user.is_active else '비활성화'
    messages.success(request, f"'{user.username}' 계정이 {status}되었습니다.")
    return redirect('accounts:admin_user_list')


@login_required
def admin_user_delete(request, pk):
    if request.user.role != 'manager':
        return redirect('reports:list')
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, '자기 자신의 계정은 삭제할 수 없습니다.')
        return redirect('accounts:admin_user_list')
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"'{username}' 계정이 삭제되었습니다.")
        return redirect('accounts:admin_user_list')
    return redirect('accounts:admin_user_list')
