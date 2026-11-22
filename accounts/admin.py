from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'department', 'role', 'organization', 'can_download_weekly', 'is_active']
    list_filter = ['role', 'department', 'organization', 'can_download_weekly', 'is_active']
    list_editable = ['can_download_weekly']
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('role', 'organization', 'department', 'phone', 'emoji')}),
        ('보고서 권한', {'fields': ('can_download_weekly',)}),
    )
