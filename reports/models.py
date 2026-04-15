from django.db import models
from django.conf import settings
from django.utils import timezone


class DailyReport(models.Model):
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('submitted', '제출완료'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='작성자'
    )
    report_date = models.DateField(verbose_name='보고 날짜')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='상태')

    # 업무 내용
    completed_tasks = models.TextField(verbose_name='금일 완료 업무', blank=True)
    in_progress_tasks = models.TextField(verbose_name='진행 중 업무', blank=True)
    tomorrow_tasks = models.TextField(verbose_name='내일 예정 업무', blank=True)
    issues = models.TextField(verbose_name='이슈 및 특이사항', blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '일일 업무보고서'
        verbose_name_plural = '일일 업무보고서 목록'
        ordering = ['-report_date', '-created_at']
        unique_together = ['author', 'report_date']

    def __str__(self):
        return f'{self.author} - {self.report_date} ({self.get_status_display()})'


class TaskItem(models.Model):
    CATEGORY_CHOICES = [
        ('completed', '완료'),
        ('in_progress', '진행중'),
        ('tomorrow', '예정'),
    ]

    report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='task_items', verbose_name='보고서')
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, verbose_name='분류')
    content = models.CharField(max_length=500, verbose_name='업무 내용')
    progress = models.IntegerField(default=0, verbose_name='진행률(%)')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')

    class Meta:
        verbose_name = '업무 항목'
        verbose_name_plural = '업무 항목 목록'
        ordering = ['order']

    def __str__(self):
        return f'[{self.get_category_display()}] {self.content}'


class DailyTask(models.Model):
    STATUS_CHOICES = [
        ('doing', '진행중'),
        ('hold', '보류'),
        ('done', '완료'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_tasks',
        verbose_name='작성자'
    )
    start_date = models.DateField(default=timezone.localdate, verbose_name='업무 시작일자')
    end_date = models.DateField(null=True, blank=True, verbose_name='목표 완료일')
    completed_date = models.DateField(null=True, blank=True, verbose_name='완료일')
    task_name = models.CharField(max_length=300, verbose_name='업무명')
    progress = models.IntegerField(default=0, verbose_name='진행도(%)')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='doing', verbose_name='상태')
    note = models.TextField(blank=True, verbose_name='비고')
    is_reviewed = models.BooleanField(default=False, verbose_name='검토 완료')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_tasks',
        verbose_name='검토자'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='검토 일시')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '일일 업무'
        verbose_name_plural = '일일 업무 목록'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return f'{self.task_name} ({self.user.get_full_name() or self.user.username})'

    def save(self, *args, **kwargs):
        self.progress = max(0, min(100, self.progress))
        if self.progress == 100:
            self.status = 'done'
            if not self.completed_date:
                self.completed_date = timezone.localdate()
        elif self.status == 'done' and self.progress < 100:
            self.status = 'doing'
            self.completed_date = None
        super().save(*args, **kwargs)

    def recalculate_progress(self):
        """서브 업무 기반으로 진행도 자동 계산 후 저장"""
        subtasks = self.subtasks.all()
        if not subtasks.exists():
            return
        total = subtasks.count()
        done = subtasks.filter(is_done=True).count()
        progress = int(done / total * 100)
        status = self.status
        completed = None
        if progress == 100:
            status = 'done'
            completed = self.completed_date or timezone.localdate()
        elif status == 'done' and progress < 100:
            status = 'doing'
        DailyTask.objects.filter(pk=self.pk).update(
            progress=progress, status=status, completed_date=completed
        )


class SubTask(models.Model):
    daily_task = models.ForeignKey(
        DailyTask, on_delete=models.CASCADE,
        related_name='subtasks', verbose_name='메인 업무'
    )
    title = models.CharField(max_length=300, verbose_name='서브 업무명')
    is_done = models.BooleanField(default=False, verbose_name='완료 여부')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '서브 업무'
        verbose_name_plural = '서브 업무 목록'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'{self.daily_task.task_name} > {self.title}'


class OperationsDailyData(models.Model):
    """용산어린이정원 일일보고 - 수기 입력 항목"""
    report_date = models.DateField(unique=True, verbose_name='보고 날짜')

    # 방문현황
    today_total      = models.PositiveIntegerField(default=0, verbose_name='금일 입장 총수')
    main_gate_walk   = models.PositiveIntegerField(default=0, verbose_name='주출입구 도보')
    sub_gate_walk    = models.PositiveIntegerField(default=0, verbose_name='부출입구 도보')
    car_visit        = models.PositiveIntegerField(default=0, verbose_name='차량방문')
    yesterday_total  = models.PositiveIntegerField(default=0, verbose_name='전일 입장 총수')

    # 명일 기상상황
    tomorrow_temp_min  = models.IntegerField(default=0, verbose_name='명일 기온 최저(°)')
    tomorrow_temp_max  = models.IntegerField(default=0, verbose_name='명일 기온 최고(°)')
    tomorrow_rain_pct  = models.PositiveIntegerField(default=0, verbose_name='명일 강수확률(%)')

    # 운영관리 점검 (구역별)
    facility_interior = models.TextField(blank=True, verbose_name='내부시설')
    facility_outdoor  = models.TextField(blank=True, verbose_name='잔디마당·가로수길·전망언덕')
    facility_fountain = models.TextField(blank=True, verbose_name='분수정원·잼잼카페')

    # 주차장 (대수)
    parking_family   = models.PositiveIntegerField(default=0, verbose_name='다둥이')
    parking_disabled = models.PositiveIntegerField(default=0, verbose_name='장애인')
    parking_pregnant = models.PositiveIntegerField(default=0, verbose_name='임산부')
    parking_children = models.PositiveIntegerField(default=0, verbose_name='어린이단체')

    # 행사
    internal_event = models.TextField(blank=True, verbose_name='내부행사/프로그램')
    external_event = models.TextField(blank=True, verbose_name='외부행사')

    # 특이사항
    special_notes = models.TextField(blank=True, verbose_name='특이사항')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='작성자'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '일일보고 운영데이터'
        verbose_name_plural = '일일보고 운영데이터 목록'
        ordering = ['-report_date']

    def __str__(self):
        return f'운영데이터 {self.report_date}'
