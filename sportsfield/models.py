from django.conf import settings
from django.db import models

FIELD_CHOICES = [
    ('baseball', '어린이 야구장'),
    ('soccer', '축구장'),
    ('tennis_grass', '테니스장 잔디코트'),
    ('tennis_hard', '테니스장 하드코트'),
]


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('confirmed', '예약완료'),
        ('cancelled', '예약취소'),
    ]

    # 기본 크롤링 필드
    field_type = models.CharField(max_length=20, choices=FIELD_CHOICES)
    reservation_date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    applicant_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    rv_no = models.IntegerField(unique=True)
    scraped_at = models.DateTimeField(auto_now=True)

    # 상세 페이지 추가 필드
    reservation_number = models.CharField(max_length=60, blank=True)
    birth_date = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.CharField(max_length=100, blank=True)
    organization = models.CharField(max_length=100, blank=True)
    total_users = models.PositiveIntegerField(null=True, blank=True)
    scoreboard = models.CharField(max_length=20, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    adult_count = models.PositiveIntegerField(null=True, blank=True)
    child_count = models.PositiveIntegerField(null=True, blank=True)
    rv_status = models.CharField(max_length=20, blank=True)

    # 실제 이용인원 (수기 입력)
    actual_adult_count = models.PositiveIntegerField(null=True, blank=True)
    actual_child_count = models.PositiveIntegerField(null=True, blank=True)
    is_noshow = models.BooleanField(default=False)
    usage_memo = models.TextField(blank=True)

    class Meta:
        ordering = ['reservation_date', 'time_start']

    def __str__(self):
        return f"[{self.get_field_type_display()}] {self.reservation_date} {self.time_start}~{self.time_end} {self.applicant_name}"


class SportsfieldEntry(models.Model):
    CATEGORY_CHOICES = [
        ('normal', '일반'),
        ('quarter', '쿼터'),
        ('event', '행사'),
        ('other', '기타'),
    ]

    field_type = models.CharField(max_length=20, choices=FIELD_CHOICES)
    entry_date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    # 예약인원 (추가 시 수기 입력)
    reserved_adult_count = models.PositiveIntegerField(null=True, blank=True)
    reserved_child_count = models.PositiveIntegerField(null=True, blank=True)

    # 실제 이용인원 (이용현황에서 수기 입력)
    actual_adult_count = models.PositiveIntegerField(null=True, blank=True)
    actual_child_count = models.PositiveIntegerField(null=True, blank=True)
    is_noshow = models.BooleanField(default=False)
    usage_memo = models.TextField(blank=True)

    class Meta:
        ordering = ['entry_date', 'time_start']

    def __str__(self):
        return f"[{self.get_field_type_display()}] {self.entry_date} {self.get_category_display()} {self.title}"
