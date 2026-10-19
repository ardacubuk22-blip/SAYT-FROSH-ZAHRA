from django.db import models
from django.utils import timezone

from core.models import City, District
from sources.models import Source


class ApprovalStatus(models.TextChoices):
    """Iranian ministry recognition. Entered by hand only — no AI or crawler may ever set it."""

    UNKNOWN = "unknown", "بررسی نشده"
    APPROVED = "approved", "تأیید شده"
    NOT_APPROVED = "not_approved", "تأیید نشده"


class University(models.Model):
    class Ownership(models.TextChoices):
        STATE = "state", "دولتی"
        FOUNDATION = "foundation", "وقفی (Vakıf)"

    name = models.CharField("نام (ترکی)", max_length=255)
    name_fa = models.CharField("نام فارسی", max_length=255, blank=True)
    slug = models.SlugField("نشانی کوتاه", unique=True)
    ownership = models.CharField("نوع", max_length=20, choices=Ownership.choices)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="universities", verbose_name="شهر")
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="universities", verbose_name="محله"
    )
    has_dormitory = models.BooleanField("خوابگاه", null=True, blank=True, help_text="خالی = نامشخص")
    official_url = models.URLField("لینک رسمی", max_length=1000, blank=True)
    international_url = models.URLField("صفحه‌ی دانشجوی خارجی", max_length=1000, blank=True)
    description_fa = models.TextField("توضیح فارسی", blank=True)
    is_published = models.BooleanField("منتشر شود", default=True)

    # Manual only. Never filled by the data engine.
    science_ministry_status = models.CharField(
        "تأیید وزارت علوم ایران", max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.UNKNOWN
    )
    science_ministry_checked = models.DateField("تاریخ آخرین بررسی (وزارت علوم)", null=True, blank=True)

    # Source tracking
    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True, related_name="universities", verbose_name="منبع"
    )
    last_checked = models.DateTimeField("آخرین بررسی منبع", null=True, blank=True)

    class Meta:
        verbose_name = "دانشگاه"
        verbose_name_plural = "دانشگاه‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name_fa or self.name

    @property
    def code(self):
        return f"UN-{self.pk}"


class Program(models.Model):
    class Level(models.TextChoices):
        ASSOCIATE = "associate", "کاردانی"
        BACHELOR = "bachelor", "کارشناسی"
        MASTER = "master", "کارشناسی ارشد"
        PHD = "phd", "دکتری"

    class Language(models.TextChoices):
        TURKISH = "tr", "ترکی"
        ENGLISH = "en", "انگلیسی"
        OTHER = "other", "سایر"

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs", verbose_name="دانشگاه")
    name = models.CharField("نام رشته (ترکی/انگلیسی)", max_length=255)
    name_fa = models.CharField("نام فارسی رشته", max_length=255, blank=True)
    level = models.CharField("مقطع", max_length=20, choices=Level.choices)
    language = models.CharField("زبان تحصیل", max_length=10, choices=Language.choices, default=Language.TURKISH)
    tuition_foreign = models.DecimalField("شهریه‌ی دانشجوی خارجی (سالانه)", max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField("واحد پول", max_length=3, default="TRY")
    academic_year = models.CharField("سال تحصیلی", max_length=9, blank=True, help_text="مثلاً 2026-2027")
    is_medical = models.BooleanField("رشته‌ی پزشکی", default=False)

    # Manual only. Relevant for medical programs.
    health_ministry_status = models.CharField(
        "تأیید وزارت بهداشت", max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.UNKNOWN
    )
    health_ministry_checked = models.DateField("تاریخ آخرین بررسی (وزارت بهداشت)", null=True, blank=True)

    source_url = models.URLField("لینک منبع", max_length=1000, blank=True)
    last_checked = models.DateTimeField("آخرین بررسی منبع", null=True, blank=True)

    class Meta:
        verbose_name = "رشته"
        verbose_name_plural = "رشته‌ها"
        ordering = ["university", "level", "name"]

    def __str__(self):
        return f"{self.name_fa or self.name} — {self.university}"


class AdmissionCycle(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="cycles", verbose_name="رشته")
    registration_start = models.DateField("شروع ثبت‌نام", null=True, blank=True)
    registration_end = models.DateField("پایان ثبت‌نام", null=True, blank=True)
    requirements = models.TextField("شرایط", blank=True)
    documents = models.TextField("مدارک لازم", blank=True)
    registration_url = models.URLField("لینک ثبت‌نام", max_length=1000, blank=True)
    scholarship = models.TextField("بورسیه", blank=True)
    source_url = models.URLField("لینک منبع", max_length=1000, blank=True)
    last_checked = models.DateTimeField("آخرین بررسی منبع", null=True, blank=True)

    class Meta:
        verbose_name = "دوره‌ی پذیرش"
        verbose_name_plural = "دوره‌های پذیرش"
        ordering = ["-registration_end", "-registration_start"]

    def __str__(self):
        return f"{self.program} ({self.registration_start or '?'} → {self.registration_end or '?'})"

    @property
    def is_open(self):
        today = timezone.localdate()
        if self.registration_end and self.registration_end < today:
            return False
        if self.registration_start and self.registration_start > today:
            return False
        return bool(self.registration_start or self.registration_end)
