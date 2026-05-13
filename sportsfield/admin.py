from django.contrib import admin
from .models import Reservation, SportsfieldEntry


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'reservation_date', 'field_type', 'time_start', 'time_end',
        'applicant_name', 'organization', 'status', 'rv_no',
    )
    list_filter = ('field_type', 'status', 'reservation_date')
    search_fields = ('applicant_name', 'organization', 'phone', 'email', 'reservation_number')
    date_hierarchy = 'reservation_date'
    ordering = ('-reservation_date', 'time_start')


@admin.register(SportsfieldEntry)
class SportsfieldEntryAdmin(admin.ModelAdmin):
    list_display = (
        'entry_date', 'field_type', 'time_start', 'time_end',
        'title', 'category', 'author',
    )
    list_filter = ('field_type', 'category', 'entry_date')
    search_fields = ('title', 'usage_memo', 'author__username')
    date_hierarchy = 'entry_date'
    ordering = ('-entry_date', 'time_start')
