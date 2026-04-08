from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'department', 'role', 'is_active']
    list_filter = ['role', 'department', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('role', 'department', 'phone')}),
    )
