from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('staff', '직원'),
        ('up_staff', '운영사무국직원'),
        ('manager', '관리자'),
    ]
    ORGANIZATION_CHOICES = [
        ('operations', '운영사무국'),
        ('parking', '보안팀'),
        ('info', '안내센터'),
        ('sportsfield', '스포츠필드'),
        ('dreammarket', '꿈나래마켓'),
        ('eulrimcafe', '카페어울림'),
        ('jemjemcafe', '잼잼카페'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff', verbose_name='역할')
    emoji = models.CharField(max_length=10, blank=True, verbose_name='이모지')
    department = models.CharField(max_length=100, blank=True, verbose_name='부서')
    phone = models.CharField(max_length=20, blank=True, verbose_name='연락처')
    organization = models.CharField(
        max_length=20, choices=ORGANIZATION_CHOICES,
        default='operations', verbose_name='소속'
    )

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_organization_display()})'

    def get_full_name(self):
        full_name = f"{self.last_name}{self.first_name}"
        return full_name.strip()

    @property
    def can_access_parking(self):
        return self.organization in ('operations', 'parking')

    @property
    def can_access_info(self):
        return self.organization in ('operations', 'info')

    @property
    def can_access_operations(self):
        return self.organization == 'operations'

    @property
    def can_access_sportsfield(self):
        return self.organization in ('operations', 'info', 'sportsfield')

    @property
    def can_access_facilities(self):
        return self.organization in ('operations', 'dreammarket', 'eulrimcafe', 'jemjemcafe')

    @property
    def can_access_kumnare(self):
        return self.organization in ('operations', 'dreammarket')

    @property
    def can_access_eoulrim(self):
        return self.organization in ('operations', 'eulrimcafe')

    @property
    def can_access_jamjam(self):
        return self.organization in ('operations', 'jemjemcafe')
