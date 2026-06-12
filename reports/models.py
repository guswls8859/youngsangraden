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
    completed_date = models.DateField(null=True, blank=True, verbose_name='완료 일자')
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
    godata_total     = models.PositiveIntegerField(default=0, verbose_name='GODATA 도보 합계')  # GODATA 원본값
    today_total      = models.PositiveIntegerField(default=0, verbose_name='금일 입장 총수')    # godata_total + car_visit
    main_gate_walk   = models.PositiveIntegerField(default=0, verbose_name='주출입구 도보')
    sub_gate_walk    = models.PositiveIntegerField(default=0, verbose_name='부출입구 도보')
    car_visit        = models.PositiveIntegerField(default=0, verbose_name='차량방문')
    yesterday_total  = models.PositiveIntegerField(default=0, verbose_name='전일 입장 총수')

    # 시간대별 입장 — 주출입구 / 부출입구 분리 저장 (GODATA 시간대별 구역비교)
    slot_0900_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='09:00 주출입구')
    slot_0900_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='09:00 부출입구')
    slot_1000_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='10:00 주출입구')
    slot_1000_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='10:00 부출입구')
    slot_1100_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='11:00 주출입구')
    slot_1100_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='11:00 부출입구')
    slot_1200_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='12:00 주출입구')
    slot_1200_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='12:00 부출입구')
    slot_1300_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='13:00 주출입구')
    slot_1300_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='13:00 부출입구')
    slot_1400_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='14:00 주출입구')
    slot_1400_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='14:00 부출입구')
    slot_1500_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='15:00 주출입구')
    slot_1500_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='15:00 부출입구')
    slot_1600_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='16:00 주출입구')
    slot_1600_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='16:00 부출입구')
    slot_1700_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='17:00 주출입구')
    slot_1700_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='17:00 부출입구')
    slot_1800_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='18:00 주출입구')
    slot_1800_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='18:00 부출입구')
    slot_1900_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='19:00 주출입구')
    slot_1900_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='19:00 부출입구')
    slot_2000_main = models.PositiveIntegerField(null=True, blank=True, verbose_name='20:00 주출입구')
    slot_2000_sub  = models.PositiveIntegerField(null=True, blank=True, verbose_name='20:00 부출입구')

    # 명일 기상상황
    tomorrow_temp_min  = models.IntegerField(default=0, verbose_name='명일 기온 최저(°)')
    tomorrow_temp_max  = models.IntegerField(default=0, verbose_name='명일 기온 최고(°)')
    tomorrow_rain_pct  = models.PositiveIntegerField(default=0, verbose_name='명일 강수확률(%)')

    # 운영관리 점검 (구역별)
    facility_interior = models.TextField(blank=True, verbose_name='내부시설')
    facility_outdoor  = models.TextField(blank=True, verbose_name='잔디마당·가로수길·전망언덕')
    facility_fountain = models.TextField(blank=True, verbose_name='분수정원·잼잼카페')

    # 작업사진 캡션 (사진은 FacilityWorkPhoto에 category별로 저장)
    facility_interior_caption = models.CharField(max_length=200, blank=True, verbose_name='내부시설 작업사진 캡션')
    facility_outdoor_caption  = models.CharField(max_length=200, blank=True, verbose_name='잔디마당·가로수길·전망언덕 작업사진 캡션')
    facility_fountain_caption = models.CharField(max_length=200, blank=True, verbose_name='분수정원·잼잼카페 작업사진 캡션')

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

    # 편익시설 매출 수기 입력 (facility 보고서 없을 때 사용)
    manual_eoulrim_sales = models.PositiveIntegerField(default=0, verbose_name='카페어울림 수기매출')
    manual_jamjam_sales  = models.PositiveIntegerField(default=0, verbose_name='잼잼카페 수기매출')
    manual_kumnare_sales = models.PositiveIntegerField(default=0, verbose_name='꿈나래마켓 수기매출')

    # 세부 이용현황 수기 입력 (각 부서 보고서 없을 때 사용)
    manual_shuttle_total = models.PositiveIntegerField(default=0, verbose_name='셔틀버스 수기 인원')
    manual_rental_total  = models.PositiveIntegerField(default=0, verbose_name='대여물품 수기 인원')
    manual_stamp_total   = models.PositiveIntegerField(default=0, verbose_name='스탬프투어 수기 인원')

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


class InternalEvent(models.Model):
    """일일보고 내부행사/프로그램 항목 — 행사명 + 자유 컬럼 테이블"""
    ops = models.ForeignKey(
        OperationsDailyData, on_delete=models.CASCADE,
        related_name='internal_events', verbose_name='일일보고'
    )
    name = models.CharField(max_length=200, verbose_name='행사명')
    # 자유 컬럼: [{'header': '운영시간', 'value': '13:40~15:00'}, ...]
    columns_json = models.JSONField(default=list, blank=True, verbose_name='컬럼')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '내부행사/프로그램'
        verbose_name_plural = '내부행사/프로그램 목록'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'[{self.ops.report_date}] {self.name}'


class ExternalEvent(models.Model):
    """일일보고 외부행사 항목 — 행사명 + 자유 컬럼 테이블"""
    ops = models.ForeignKey(
        OperationsDailyData, on_delete=models.CASCADE,
        related_name='external_events', verbose_name='일일보고'
    )
    name = models.CharField(max_length=200, verbose_name='행사명')
    columns_json = models.JSONField(default=list, blank=True, verbose_name='컬럼')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '외부행사'
        verbose_name_plural = '외부행사 목록'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'[{self.ops.report_date}] {self.name}'


class VacationRequest(models.Model):
    """휴가 신청 — 직원이 신청, 관리자가 승인/반려"""
    LEAVE_TYPE_CHOICES = [
        ('annual',     '연차'),
        ('half',       '반차'),
        ('quarter',    '반반차'),
        ('sick',       '병가'),
        ('etc',        '기타'),
    ]
    HALF_PERIOD_CHOICES = [
        ('am', '오전'),
        ('pm', '오후'),
    ]
    STATUS_CHOICES = [
        ('pending',  '대기'),
        ('approved', '승인'),
        ('rejected', '반려'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vacation_requests',
        verbose_name='신청자',
    )
    leave_type   = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES, verbose_name='휴가 종류')
    start_date   = models.DateField(verbose_name='시작일')
    end_date     = models.DateField(verbose_name='종료일')
    half_period  = models.CharField(
        max_length=2, choices=HALF_PERIOD_CHOICES,
        blank=True, verbose_name='반차/반반차 시간대'
    )
    reason       = models.TextField(blank=True, verbose_name='사유')

    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='상태')
    reviewed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_vacations',
        verbose_name='검토자',
    )
    reviewed_at     = models.DateTimeField(null=True, blank=True, verbose_name='검토 일시')
    review_comment  = models.TextField(blank=True, verbose_name='검토 메모')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '휴가 신청'
        verbose_name_plural = '휴가 신청 목록'
        ordering = ['-start_date', '-created_at']

    def __str__(self):
        return f'{self.user} {self.start_date}~{self.end_date} {self.get_leave_type_display()} ({self.get_status_display()})'


class LadderGame(models.Model):
    """사다리 타기 게임 — 운영사무국 전체 공유"""
    title       = models.CharField(max_length=100, blank=True, verbose_name='제목')
    players     = models.JSONField(default=list, verbose_name='참가자')
    results     = models.JSONField(default=list, verbose_name='결과')
    rungs       = models.JSONField(default=list, verbose_name='가로줄(ROWS x N-1)')
    revealed    = models.JSONField(default=dict, verbose_name='공개된 결과 {start_col: end_col}')
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_ladder_games',
        verbose_name='생성자',
    )
    is_active   = models.BooleanField(default=True, verbose_name='진행중')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '사다리 게임'
        verbose_name_plural = '사다리 게임 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title or "사다리"} ({self.created_at:%m-%d %H:%M})'

    def is_fully_revealed(self):
        return len(self.revealed) >= len(self.players)


class DutyShift(models.Model):
    """당직 근무 — 관리자가 등록·편집"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='duty_shifts',
        verbose_name='담당자',
    )
    date = models.DateField(verbose_name='근무일')
    note = models.CharField(max_length=200, blank=True, verbose_name='비고')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_duties',
        verbose_name='등록자',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '당직 근무'
        verbose_name_plural = '당직 근무 목록'
        ordering = ['-date']
        unique_together = ['user', 'date']

    def __str__(self):
        return f'{self.date} {self.user}'


class FacilityWorkPhoto(models.Model):
    """일일보고 운영관리 작업사진 (구역별)"""
    CATEGORY_CHOICES = [
        ('interior', '내부시설'),
        ('outdoor',  '잔디마당·가로수길·전망언덕'),
        ('fountain', '분수정원·잼잼카페'),
    ]
    ops = models.ForeignKey(
        OperationsDailyData, on_delete=models.CASCADE,
        related_name='work_photos', verbose_name='일일보고'
    )
    category = models.CharField(
        max_length=10, choices=CATEGORY_CHOICES, default='interior',
        verbose_name='구역',
    )
    image = models.ImageField(upload_to='work_photos/%Y/%m/', verbose_name='사진')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '운영관리 작업사진'
        verbose_name_plural = '운영관리 작업사진 목록'
        ordering = ['category', 'order', 'created_at']

    def __str__(self):
        return f'[{self.ops.report_date}] {self.get_category_display()} #{self.order}'
