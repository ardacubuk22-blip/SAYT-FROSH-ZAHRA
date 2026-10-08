from django.db import models


class City(models.Model):
    """A city we cover. Version 1 has only Istanbul, but every record points to a city."""

    name = models.CharField("نام (ترکی/انگلیسی)", max_length=100, unique=True)
    name_fa = models.CharField("نام فارسی", max_length=100)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ["name"]

    def __str__(self):
        return self.name_fa or self.name


class District(models.Model):
    """A district (ilçe) inside a city, e.g. Beyoğlu or Kadıköy."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="districts", verbose_name="شهر")
    name = models.CharField("نام", max_length=100)
    name_fa = models.CharField("نام فارسی", max_length=100, blank=True)

    class Meta:
        verbose_name = "محله"
        verbose_name_plural = "محله‌ها"
        ordering = ["city", "name"]
        constraints = [models.UniqueConstraint(fields=["city", "name"], name="unique_district_per_city")]

    def __str__(self):
        return self.name_fa or self.name


class Venue(models.Model):
    """A place where events happen (concert hall, museum, park...)."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="venues", verbose_name="شهر")
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="venues", verbose_name="محله"
    )
    name = models.CharField("نام", max_length=255)
    address = models.CharField("آدرس", max_length=500, blank=True)

    class Meta:
        verbose_name = "مکان"
        verbose_name_plural = "مکان‌ها"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["city", "name"], name="unique_venue_per_city")]

    def __str__(self):
        return self.name


class Interaction(models.Model):
    """Anonymous record of a page view or WhatsApp click, kept only after the visitor agreed.

    No name, phone, IP or user agent is stored: only a random id from the visitor's own cookie.
    This is the raw material for a future recommendation system.
    """

    class Kind(models.TextChoices):
        VIEW = "view", "بازدید"
        WHATSAPP = "whatsapp", "کلیک واتساپ"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    object_type = models.CharField(max_length=20, help_text="event / tour / university")
    object_id = models.PositiveIntegerField()
    visitor_id = models.CharField("شناسه‌ی ناشناس", max_length=36, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "بازدید/کلیک"
        verbose_name_plural = "بازدیدها و کلیک‌ها"
        ordering = ["-created_at"]
