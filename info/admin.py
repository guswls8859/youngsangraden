from django.contrib import admin
from .models import InfoReport


@admin.register(InfoReport)
class InfoReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'status', 'shuttle_total', 'created_at')
    list_filter = ('status', 'report_date')
    search_fields = ('author__username', 'author__last_name')
    ordering = ('-report_date',)
