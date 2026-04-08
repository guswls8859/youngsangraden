from django.conf import settings
from django.db import models


class EventhouseRecord(models.Model):
    space_name = models.CharField(max_length=100, verbose_name='공간명')
    title = models.CharField(max_length=200, verbose_name='사용자/내용')
    record_date = models.DateField(verbose_name='날짜')
    time_start = models.TimeField(null=True, blank=True, verbose_name='시작 시간')
    time_end = models.TimeField(null=True, blank=True, verbose_name='종료 시간')
    memo = models.TextField(blank=True, verbose_name='메모')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['record_date', 'time_start']

    def __str__(self):
        return f'[{self.space_name}] {self.record_date} {self.title}'
