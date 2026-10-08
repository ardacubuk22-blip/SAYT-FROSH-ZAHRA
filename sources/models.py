from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Source(models.Model):
    """A website or API we collect data from. Each one has its own adapter."""

    class AccessMethod(models.TextChoices):
        API = "api", "API"
        RSS = "rss", "RSS"
        OPEN_DATA = "open_data", "داده‌ی باز"
        CRAWLER = "crawler", "خزنده (crawler)"

    class TermsStatus(models.TextChoices):
        ALLOWED = "allowed", "مجاز"
        NEEDS_PARTNERSHIP = "needs_partnership", "نیاز به همکاری رسمی"
        FORBIDDEN = "forbidden", "ممنوع"

    class Type(models.TextChoices):
        EVENTS = "events", "رویداد"
        VENUES = "venues", "مکان"
        UNIVERSITY = "university", "دانشگاه"

    name = models.CharField("نام", max_length=200)
    adapter = models.SlugField(
        "کد adapter", unique=True, help_text="نام فایل adapter در پوشه‌ی sources/adapters"
    )
    url = models.URLField("آدرس")
    type = models.CharField("نوع", max_length=20, choices=Type.choices, default=Type.EVENTS)
    access_method = models.CharField("روش دسترسی", max_length=20, choices=AccessMethod.choices)
    check_frequency = models.DurationField("فاصله‌ی بررسی", default=timezone.timedelta(days=1))
    terms_status = models.CharField(
        "وضعیت قوانین سایت", max_length=20, choices=TermsStatus.choices, default=TermsStatus.ALLOWED
    )
    is_active = models.BooleanField("فعال", default=True)
    last_run = models.DateTimeField("آخرین اجرا", null=True, blank=True)
    last_success = models.DateTimeField("آخرین اجرای موفق", null=True, blank=True)
    items_found_last_run = models.PositiveIntegerField("تعداد پیدا شده در آخرین اجرا", null=True, blank=True)
    last_error = models.TextField("آخرین خطا", blank=True)
    notes = models.TextField("یادداشت", blank=True)

    class Meta:
        verbose_name = "منبع"
        verbose_name_plural = "منابع"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def needs_attention(self):
        """True when the last run failed or found nothing — shown as an alert in the admin."""
        if self.last_run is None:
            return False
        return bool(self.last_error) or not self.items_found_last_run

    def is_due(self, now=None):
        now = now or timezone.now()
        return self.last_run is None or now - self.last_run >= self.check_frequency

    def can_run(self):
        return self.is_active and self.terms_status == self.TermsStatus.ALLOWED


class SourceRun(models.Model):
    """One execution of a source adapter, kept for the health page."""

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="runs", verbose_name="منبع")
    started_at = models.DateTimeField("شروع", auto_now_add=True)
    finished_at = models.DateTimeField("پایان", null=True, blank=True)
    links_found = models.PositiveIntegerField("لینک‌های پیدا شده", default=0)
    unchanged = models.PositiveIntegerField("بدون تغییر", default=0)
    created = models.PositiveIntegerField("جدید", default=0)
    updated = models.PositiveIntegerField("به‌روز شده", default=0)
    sent_to_review = models.PositiveIntegerField("به صف بررسی", default=0)
    failed = models.PositiveIntegerField("ناموفق", default=0)
    error = models.TextField("خطا", blank=True)

    class Meta:
        verbose_name = "اجرای منبع"
        verbose_name_plural = "اجراهای منابع"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} @ {self.started_at:%Y-%m-%d %H:%M}"


class PageSnapshot(models.Model):
    """The last cleaned text hash of every page we fetched, so unchanged pages skip the AI."""

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="pages", verbose_name="منبع")
    url = models.URLField("آدرس صفحه", max_length=1000, unique=True)
    content_hash = models.CharField("هش محتوا", max_length=64)
    first_seen = models.DateTimeField("اولین بار دیده شده", auto_now_add=True)
    last_checked = models.DateTimeField("آخرین بررسی")
    last_changed = models.DateTimeField("آخرین تغییر")

    class Meta:
        verbose_name = "صفحه‌ی بررسی‌شده"
        verbose_name_plural = "صفحه‌های بررسی‌شده"

    def __str__(self):
        return self.url


class ApiUsage(models.Model):
    """Every Claude API call with its token counts and cost, for the monthly cost report."""

    class Purpose(models.TextChoices):
        EXTRACTION = "extraction", "استخراج"
        TRANSLATION = "translation", "ترجمه"

    created_at = models.DateTimeField("زمان", auto_now_add=True)
    model = models.CharField("مدل", max_length=100)
    purpose = models.CharField("کاربرد", max_length=20, choices=Purpose.choices)
    is_batch = models.BooleanField("Batch", default=False)
    input_tokens = models.PositiveIntegerField("توکن ورودی", default=0)
    output_tokens = models.PositiveIntegerField("توکن خروجی", default=0)
    cost_usd = models.DecimalField("هزینه (دلار)", max_digits=10, decimal_places=6, default=0)
    source_url = models.URLField("صفحه", max_length=1000, blank=True)

    class Meta:
        verbose_name = "مصرف API"
        verbose_name_plural = "مصرف API"
        ordering = ["-created_at"]

    @classmethod
    def month_total(cls, now=None):
        now = now or timezone.localtime()
        total = cls.objects.filter(created_at__year=now.year, created_at__month=now.month).aggregate(
            total=Sum("cost_usd")
        )["total"]
        return total or Decimal("0")
