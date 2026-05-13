from django.contrib import admin
from .models import Vehicle, ParkingLog


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('car_number', 'organization', 'phone', 'start_date', 'end_date', 'registered_by', 'created_at')
    list_filter = ('organization', 'start_date', 'end_date')
    search_fields = ('car_number', 'organization', 'phone')
    date_hierarchy = 'start_date'
    ordering = ('-created_at',)


@admin.register(ParkingLog)
class ParkingLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'vehicle', 'status', 'entered_at', 'exited_at', 'updated_by')
    list_filter = ('status', 'date')
    search_fields = ('vehicle__car_number', 'vehicle__organization')
    date_hierarchy = 'date'
    ordering = ('-date',)
    autocomplete_fields = ('vehicle',)
