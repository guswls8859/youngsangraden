from django.db import models
from django.conf import settings


class Vehicle(models.Model):
    """출입 차량 등록 정보"""
    organization = models.CharField(max_length=100, verbose_name='소속')
    car_number = models.CharField(max_length=20, verbose_name='차량 번호')
    phone = models.CharField(max_length=20, blank=True, verbose_name='핸드폰 번호')
    start_date = models.DateField(verbose_name='출입 시작일')
    end_date = models.DateField(verbose_name='출입 종료일')
    note = models.TextField(blank=True, verbose_name='비고')
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registered_vehicles',
        verbose_name='등록자'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '차량'
        verbose_name_plural = '차량 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.car_number} ({self.organization})'

    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.localdate()
        return self.start_date <= today <= self.end_date

    def today_log(self):
        from django.utils import timezone
        today = timezone.localdate()
        return self.logs.filter(date=today).first()


class ParkingLog(models.Model):
    """일별 입출차 기록"""
    STATUS_CHOICES = [
        ('waiting', '대기중'),
        ('entered', '입차'),
        ('exited', '출차'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='logs', verbose_name='차량')
    date = models.DateField(verbose_name='날짜')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting', verbose_name='상태')
    entered_at = models.DateTimeField(null=True, blank=True, verbose_name='입차 시각')
    exited_at = models.DateTimeField(null=True, blank=True, verbose_name='출차 시각')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='처리자'
    )

    class Meta:
        verbose_name = '입출차 기록'
        verbose_name_plural = '입출차 기록 목록'
        unique_together = ['vehicle', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.vehicle.car_number} {self.date} ({self.get_status_display()})'
