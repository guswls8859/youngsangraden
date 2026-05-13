from django.contrib import admin
from .models import (
    DailyReport, TaskItem,
    DailyTask, SubTask,
    OperationsDailyData,
)


class TaskItemInline(admin.TabularInline):
    model = TaskItem
    extra = 0


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'status', 'created_at')
    list_filter = ('status', 'report_date', 'author__department')
    search_fields = ('author__username', 'author__first_name', 'completed_tasks')
    inlines = (TaskItemInline,)
    date_hierarchy = 'report_date'


class SubTaskInline(admin.TabularInline):
    model = SubTask
    extra = 0
    fields = ('title', 'is_done', 'order')


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'user', 'status', 'progress', 'start_date', 'end_date', 'completed_date', 'is_reviewed')
    list_filter = ('status', 'is_reviewed', 'start_date')
    search_fields = ('task_name', 'note', 'user__username', 'user__first_name')
    date_hierarchy = 'start_date'
    inlines = (SubTaskInline,)
    ordering = ('-start_date',)


@admin.register(OperationsDailyData)
class OperationsDailyDataAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'today_total', 'godata_total', 'main_gate_walk', 'sub_gate_walk', 'car_visit', 'updated_at')
    list_filter = ('report_date',)
    search_fields = ('report_date', 'special_notes', 'internal_event', 'external_event')
    date_hierarchy = 'report_date'
    ordering = ('-report_date',)
    fieldsets = (
        ('날짜', {'fields': ('report_date',)}),
        ('방문현황', {
            'fields': ('today_total', 'godata_total', 'main_gate_walk', 'sub_gate_walk', 'car_visit', 'yesterday_total'),
        }),
        ('시간대별 입장 (주출입구/부출입구)', {
            'classes': ('collapse',),
            'fields': (
                ('slot_0900_main', 'slot_0900_sub'),
                ('slot_1000_main', 'slot_1000_sub'),
                ('slot_1100_main', 'slot_1100_sub'),
                ('slot_1200_main', 'slot_1200_sub'),
                ('slot_1300_main', 'slot_1300_sub'),
                ('slot_1400_main', 'slot_1400_sub'),
                ('slot_1500_main', 'slot_1500_sub'),
                ('slot_1600_main', 'slot_1600_sub'),
                ('slot_1700_main', 'slot_1700_sub'),
                ('slot_1800_main', 'slot_1800_sub'),
                ('slot_1900_main', 'slot_1900_sub'),
                ('slot_2000_main', 'slot_2000_sub'),
            ),
        }),
        ('명일 기상', {
            'fields': ('tomorrow_temp_min', 'tomorrow_temp_max', 'tomorrow_rain_pct'),
        }),
        ('운영관리 점검', {
            'fields': ('facility_interior', 'facility_outdoor', 'facility_fountain'),
        }),
        ('주차장', {
            'fields': ('parking_family', 'parking_disabled', 'parking_pregnant', 'parking_children'),
        }),
        ('행사·특이사항', {
            'fields': ('internal_event', 'external_event', 'special_notes'),
        }),
        ('메타', {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
