from django.db import models
from django.conf import settings


class InfoReport(models.Model):
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('submitted', '제출완료'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='info_reports',
        verbose_name='작성자'
    )
    report_date = models.DateField(verbose_name='보고 날짜')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='상태'
    )

    # 셔틀 총원 (숫자 입력)
    shuttle_total = models.PositiveIntegerField(default=0, verbose_name='셔틀 총원')

    # 특이사항 (각 섹션별)
    info_note = models.TextField(blank=True, verbose_name='인포메이션 특이사항')
    patrol_note = models.TextField(blank=True, verbose_name='순찰 특이사항')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '안내센터 보고서'
        verbose_name_plural = '안내센터 보고서 목록'
        ordering = ['-report_date', '-created_at']
        unique_together = ['author', 'report_date']

    def __str__(self):
        return f'{self.author} - {self.report_date} ({self.get_status_display()})'


class InfoReportItem(models.Model):
    SECTION_CHOICES = [
        ('info', '인포메이션'),
        ('shuttle', '셔틀'),
        ('patrol', '순찰'),
    ]

    report = models.ForeignKey(
        InfoReport, on_delete=models.CASCADE,
        related_name='items', verbose_name='보고서'
    )
    section = models.CharField(max_length=10, choices=SECTION_CHOICES, verbose_name='섹션')
    content = models.CharField(max_length=500, verbose_name='업무 내용')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')

    class Meta:
        verbose_name = '안내센터 업무 항목'
        verbose_name_plural = '안내센터 업무 항목 목록'
        ordering = ['section', 'order']

    def __str__(self):
        return f'[{self.get_section_display()}] {self.content}'
