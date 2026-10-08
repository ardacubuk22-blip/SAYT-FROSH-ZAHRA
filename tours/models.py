from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import City


class Agency(models.Model):
    """The travel agency that runs a guided tour, with its license number."""

    name = models.CharField("نام آژانس", max_length=200)
    license_number = models.CharField("شماره‌ی مجوز", max_length=100)
    notes = models.TextField("یادداشت", blank=True)

    class Meta:
        verbose_name = "آژانس"
        verbose_name_plural = "آژانس‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tour(models.Model):
    class Kind(models.TextChoices):
        GUIDED = "guided", "تور با آژانس"
        SELF_GUIDED = "self_guided", "تور خودگردان"

    kind = models.CharField("نوع", max_length=20, choices=Kind.choices, default=Kind.GUIDED)
    title = models.CharField("عنوان", max_length=300)
    description = models.TextField("توضیح", blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="tours", verbose_name="شهر")
    agency = models.ForeignKey(
        Agency, on_delete=models.PROTECT, null=True, blank=True, related_name="tours", verbose_name="آژانس برگزارکننده"
    )
    price = models.DecimalField("قیمت", max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField("واحد پول", max_length=3, default="TRY")
    capacity = models.PositiveIntegerField("ظرفیت", null=True, blank=True)
    image_url = models.URLField("تصویر", max_length=1000, blank=True)
    is_published = models.BooleanField("منتشر شود", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تور"
        verbose_name_plural = "تورها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def code(self):
        """Short code the customer sends us on WhatsApp, e.g. TR-12."""
        return f"TR-{self.pk}"

    def clean(self):
        if self.kind == self.Kind.GUIDED and not self.agency_id:
            raise ValidationError({"agency": "تور با آژانس باید آژانس و شماره‌ی مجوز داشته باشد."})

    def upcoming_dates(self):
        today = timezone.localdate()
        return self.dates.filter(start_date__gte=today)


class TourDate(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="dates", verbose_name="تور")
    start_date = models.DateField("تاریخ شروع")
    end_date = models.DateField("تاریخ پایان", null=True, blank=True)

    class Meta:
        verbose_name = "تاریخ تور"
        verbose_name_plural = "تاریخ‌های تور"
        ordering = ["start_date"]

    def __str__(self):
        return str(self.start_date)


class TourStop(models.Model):
    """One station of the itinerary. For self-guided tours the opening hours and closed days matter."""

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="stops", verbose_name="تور")
    order = models.PositiveIntegerField("ترتیب", default=1)
    name = models.CharField("نام ایستگاه", max_length=300)
    description = models.TextField("توضیح", blank=True)
    opening_hours = models.CharField("ساعت کاری", max_length=200, blank=True, help_text="مثلاً 09:00–17:00")
    closed_days = models.CharField("روزهای تعطیل", max_length=200, blank=True, help_text="مثلاً دوشنبه‌ها")

    class Meta:
        verbose_name = "ایستگاه"
        verbose_name_plural = "ایستگاه‌ها"
        ordering = ["tour", "order"]

    def __str__(self):
        return self.name
