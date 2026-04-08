from django.contrib import admin
from .models import DailyReport, TaskItem


class TaskItemInline(admin.TabularInline):
    model = TaskItem
    extra = 0


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['report_date', 'author', 'status', 'created_at']
    list_filter = ['status', 'report_date', 'author__department']
    search_fields = ['author__username', 'author__first_name', 'completed_tasks']
    inlines = [TaskItemInline]
    date_hierarchy = 'report_date'
