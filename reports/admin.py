from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DailyReport, TaskItem,
    DailyTask, SubTask,
    OperationsDailyData,
    InternalEvent, ExternalEvent, FacilityWorkPhoto,
    VacationRequest, DutyShift,
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


class InternalEventInline(admin.TabularInline):
    model = InternalEvent
    extra = 0
    fields = ('name', 'columns_json', 'order')


class ExternalEventInline(admin.TabularInline):
    model = ExternalEvent
    extra = 0
    fields = ('name', 'columns_json', 'order')


class FacilityWorkPhotoInline(admin.TabularInline):
    model = FacilityWorkPhoto
    extra = 0
    fields = ('category', 'image', 'preview', 'order')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:80px;" />', obj.image.url)
        return '-'
    preview.short_description = '미리보기'


@admin.register(OperationsDailyData)
class OperationsDailyDataAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'today_total', 'godata_total', 'main_gate_walk', 'sub_gate_walk', 'car_visit', 'updated_at')
    list_filter = ('report_date',)
    search_fields = ('report_date', 'special_notes', 'internal_event', 'external_event')
    date_hierarchy = 'report_date'
    ordering = ('-report_date',)
    inlines = (InternalEventInline, ExternalEventInline, FacilityWorkPhotoInline)
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
            'fields': (
                'facility_interior', 'facility_interior_caption',
                'facility_outdoor',  'facility_outdoor_caption',
                'facility_fountain', 'facility_fountain_caption',
            ),
        }),
        ('주차장', {
            'fields': ('parking_family', 'parking_disabled', 'parking_pregnant', 'parking_children'),
        }),
        ('행사·특이사항', {
            'fields': ('internal_event', 'external_event', 'special_notes'),
        }),
        ('편익시설 매출 (수기)', {
            'classes': ('collapse',),
            'fields': ('manual_eoulrim_sales', 'manual_jamjam_sales', 'manual_kumnare_sales'),
        }),
        ('세부 이용현황 (수기)', {
            'classes': ('collapse',),
            'fields': ('manual_shuttle_total', 'manual_rental_total', 'manual_stamp_total'),
        }),
        ('메타', {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(InternalEvent)
class InternalEventAdmin(admin.ModelAdmin):
    list_display = ('ops', 'name', 'order', 'created_at')
    list_filter = ('ops__report_date',)
    search_fields = ('name',)
    ordering = ('-ops__report_date', 'order')


@admin.register(ExternalEvent)
class ExternalEventAdmin(admin.ModelAdmin):
    list_display = ('ops', 'name', 'order', 'created_at')
    list_filter = ('ops__report_date',)
    search_fields = ('name',)
    ordering = ('-ops__report_date', 'order')


@admin.register(FacilityWorkPhoto)
class FacilityWorkPhotoAdmin(admin.ModelAdmin):
    list_display = ('ops', 'category', 'preview', 'order', 'created_at')
    list_filter = ('category', 'ops__report_date')
    ordering = ('-ops__report_date', 'category', 'order')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:80px;" />', obj.image.url)
        return '-'
    preview.short_description = '미리보기'


@admin.register(VacationRequest)
class VacationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'leave_type', 'start_date', 'end_date', 'half_period', 'status', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'reason')
    date_hierarchy = 'start_date'
    autocomplete_fields = ('user', 'reviewed_by')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('신청 정보', {
            'fields': ('user', 'leave_type', 'start_date', 'end_date', 'half_period', 'reason'),
        }),
        ('검토', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_comment'),
        }),
        ('메타', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(DutyShift)
class DutyShiftAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'note', 'created_by', 'created_at')
    list_filter = ('date',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'note')
    date_hierarchy = 'date'
    autocomplete_fields = ('user', 'created_by')
    readonly_fields = ('created_at', 'updated_at')
