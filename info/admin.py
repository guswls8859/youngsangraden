from django.contrib import admin
from .models import InfoReport, InfoReportItem


class InfoReportItemInline(admin.TabularInline):
    model = InfoReportItem
    extra = 0
    fields = ('section', 'content', 'order')


@admin.register(InfoReport)
class InfoReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'status', 'shuttle_total', 'created_at')
    list_filter = ('status', 'report_date')
    search_fields = ('author__username', 'author__last_name', 'info_note', 'patrol_note')
    date_hierarchy = 'report_date'
    ordering = ('-report_date',)
    inlines = (InfoReportItemInline,)
