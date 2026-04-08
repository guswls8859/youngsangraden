from django.db import models
from django.conf import settings


class KumnareReport(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kumnare_reports',
        verbose_name='작성자'
    )
    report_date = models.DateField(verbose_name='보고 날짜')
    sales_amount = models.PositiveIntegerField(default=0, verbose_name='매출액')
    rental_total_users = models.PositiveIntegerField(default=0, verbose_name='렌탈 총이용객')
    stamp_issued = models.PositiveIntegerField(default=0, verbose_name='스탬프투어 지급')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '꿈나래마켓 보고서'
        verbose_name_plural = '꿈나래마켓 보고서 목록'
        ordering = ['-report_date', '-created_at']

    def __str__(self):
        return f'꿈나래마켓 {self.report_date} ({self.author})'


class KumnareRentalItem(models.Model):
    report = models.ForeignKey(
        KumnareReport,
        on_delete=models.CASCADE,
        related_name='rental_items',
        verbose_name='보고서'
    )
    item_name = models.CharField(max_length=100, verbose_name='품목명')
    count = models.PositiveIntegerField(default=0, verbose_name='수량')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')

    class Meta:
        verbose_name = '렌탈 품목'
        verbose_name_plural = '렌탈 품목 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.item_name} {self.count}개'


class EoulrimReport(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='eoulrim_reports',
        verbose_name='작성자'
    )
    report_date = models.DateField(verbose_name='보고 날짜')
    daily_net_sales = models.PositiveIntegerField(default=0, verbose_name='당일 순매출(원)')
    customer_count = models.PositiveIntegerField(default=0, verbose_name='객수(명)')
    notes = models.TextField(blank=True, verbose_name='매출증감사유 및 특이사항')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '카페 어울림 보고서'
        verbose_name_plural = '카페 어울림 보고서 목록'
        ordering = ['-report_date', '-created_at']

    def __str__(self):
        return f'카페 어울림 {self.report_date} ({self.author})'

    @property
    def avg_spend(self):
        if self.customer_count:
            return round(self.daily_net_sales / self.customer_count)
        return 0


class EoulrimNewMenuItem(models.Model):
    report = models.ForeignKey(
        EoulrimReport,
        on_delete=models.CASCADE,
        related_name='new_menu_items',
        verbose_name='보고서'
    )
    name = models.CharField(max_length=100, verbose_name='메뉴명')
    count = models.PositiveIntegerField(default=0, verbose_name='판매수량')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')

    class Meta:
        verbose_name = '신메뉴 판매'
        verbose_name_plural = '신메뉴 판매 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.name} {self.count}개'


class JamjamReport(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jamjam_reports',
        verbose_name='작성자'
    )
    report_date = models.DateField(verbose_name='보고 날짜')
    daily_net_sales = models.PositiveIntegerField(default=0, verbose_name='당일 순매출(원)')
    customer_count = models.PositiveIntegerField(default=0, verbose_name='객수(명)')
    notes = models.TextField(blank=True, verbose_name='매출증감사유 및 특이사항')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        verbose_name = '잼잼카페 보고서'
        verbose_name_plural = '잼잼카페 보고서 목록'
        ordering = ['-report_date', '-created_at']

    def __str__(self):
        return f'잼잼카페 {self.report_date} ({self.author})'

    @property
    def avg_spend(self):
        if self.customer_count:
            return round(self.daily_net_sales / self.customer_count)
        return 0


class JamjamNewMenuItem(models.Model):
    report = models.ForeignKey(
        JamjamReport,
        on_delete=models.CASCADE,
        related_name='new_menu_items',
        verbose_name='보고서'
    )
    name = models.CharField(max_length=100, verbose_name='메뉴명')
    count = models.PositiveIntegerField(default=0, verbose_name='판매수량')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')

    class Meta:
        verbose_name = '신메뉴 판매'
        verbose_name_plural = '신메뉴 판매 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.name} {self.count}개'
