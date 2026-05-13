from django.contrib import admin
from .models import (
    KumnareReport, KumnareRentalItem,
    EoulrimReport, EoulrimNewMenuItem,
    JamjamReport, JamjamNewMenuItem,
)


class KumnareRentalItemInline(admin.TabularInline):
    model = KumnareRentalItem
    extra = 0


@admin.register(KumnareReport)
class KumnareReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'sales_amount', 'rental_total_users', 'stamp_issued', 'updated_at')
    list_filter = ('report_date',)
    search_fields = ('author__username', 'author__first_name')
    date_hierarchy = 'report_date'
    inlines = (KumnareRentalItemInline,)
    ordering = ('-report_date',)


class EoulrimNewMenuItemInline(admin.TabularInline):
    model = EoulrimNewMenuItem
    extra = 0


@admin.register(EoulrimReport)
class EoulrimReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'daily_net_sales', 'customer_count', 'updated_at')
    list_filter = ('report_date',)
    search_fields = ('author__username', 'author__first_name', 'notes')
    date_hierarchy = 'report_date'
    inlines = (EoulrimNewMenuItemInline,)
    ordering = ('-report_date',)


class JamjamNewMenuItemInline(admin.TabularInline):
    model = JamjamNewMenuItem
    extra = 0


@admin.register(JamjamReport)
class JamjamReportAdmin(admin.ModelAdmin):
    list_display = ('report_date', 'author', 'daily_net_sales', 'customer_count', 'updated_at')
    list_filter = ('report_date',)
    search_fields = ('author__username', 'author__first_name', 'notes')
    date_hierarchy = 'report_date'
    inlines = (JamjamNewMenuItemInline,)
    ordering = ('-report_date',)
