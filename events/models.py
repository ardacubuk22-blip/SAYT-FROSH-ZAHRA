from django.db import models

from core.models import City, District, Venue
from sources.models import Source


class Category(models.TextChoices):
    """Fixed list; the AI must pick exactly one of these keys."""

    CONCERT = "concert", "کنسرت"
    THEATRE = "theatre", "تئاتر و نمایش"
    ART_EXHIBITION = "art_exhibition", "نمایشگاه هنری"
    MUSEUM_CULTURE = "museum_culture", "موزه و رویداد فرهنگی"
    FILM_FESTIVAL = "film_festival", "جشنواره‌ی فیلم"
    ART_WORKSHOP = "art_workshop", "ورکشاپ هنری"
    SPORTS = "sports", "رویداد ورزشی"
    CITY_FESTIVAL = "city_festival", "جشنواره‌ی شهری"
    MUNICIPALITY = "municipality", "برنامه‌ی شهرداری"
    TOUR = "tour", "تور"


class Event(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "منتشر شده"
        NEEDS_REVIEW = "needs_review", "در صف بررسی"
        REJECTED = "rejected", "رد شده"

    # Content
    title = models.CharField("عنوان اصلی", max_length=500)
    title_fa = models.CharField("عنوان فارسی", max_length=500, blank=True)
    description = models.TextField("توضیح اصلی", blank=True)
    description_fa = models.TextField("توضیح فارسی", blank=True)
    category = models.CharField("دسته‌بندی", max_length=30, choices=Category.choices)
    start = models.DateTimeField("شروع")
    end = models.DateTimeField("پایان", null=True, blank=True)

    # Place
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="events", verbose_name="شهر")
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="events", verbose_name="محله"
    )
    venue = models.ForeignKey(
        Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name="events", verbose_name="مکان"
    )

    # Price
    price_min = models.DecimalField("حداقل قیمت", max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField("حداکثر قیمت", max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField("واحد پول", max_length=3, default="TRY")
    is_free = models.BooleanField("رایگان", default=False)
    ticket_url = models.URLField("لینک بلیت", max_length=1000, blank=True)
    image_url = models.URLField("تصویر", max_length=1000, blank=True)

    # Source tracking
    source = models.ForeignKey(
        Source, on_delete=models.SET_NULL, null=True, blank=True, related_name="events", verbose_name="منبع"
    )
    source_url = models.URLField("لینک منبع", max_length=1000, unique=True)
    first_seen = models.DateTimeField("اولین بار دیده شده", auto_now_add=True)
    last_checked = models.DateTimeField("آخرین بررسی", null=True, blank=True)
    last_updated = models.DateTimeField("آخرین تغییر", null=True, blank=True)
    confidence = models.FloatField("اطمینان AI", default=0)
    content_hash = models.CharField("هش محتوا", max_length=64, blank=True)
    review_reason = models.TextField("دلیل بررسی دستی", blank=True)

    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.NEEDS_REVIEW, db_index=True
    )

    class Meta:
        verbose_name = "رویداد"
        verbose_name_plural = "رویدادها"
        ordering = ["start"]

    def __str__(self):
        return self.title_fa or self.title

    @property
    def code(self):
        """Short code the customer sends us on WhatsApp, e.g. EV-1024."""
        return f"EV-{self.pk}"


class EventChange(models.Model):
    """History of price/date changes of an event."""

    TRACKED_FIELDS = ("start", "end", "price_min", "price_max", "currency", "is_free")

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="changes", verbose_name="رویداد")
    field = models.CharField("فیلد", max_length=30)
    old_value = models.CharField("مقدار قبلی", max_length=100, blank=True)
    new_value = models.CharField("مقدار جدید", max_length=100, blank=True)
    changed_at = models.DateTimeField("زمان تغییر", auto_now_add=True)

    class Meta:
        verbose_name = "تغییر رویداد"
        verbose_name_plural = "تاریخچه‌ی تغییرات"
        ordering = ["-changed_at"]
