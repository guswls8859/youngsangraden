from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    # 관리자 패널
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/create/', views.AdminUserCreateView.as_view(), name='admin_user_create'),
    path('admin/users/<int:pk>/edit/', views.AdminUserEditView.as_view(), name='admin_user_edit'),
    path('admin/users/<int:pk>/toggle/', views.admin_user_toggle_active, name='admin_user_toggle'),
    path('admin/users/<int:pk>/delete/', views.admin_user_delete, name='admin_user_delete'),
]
