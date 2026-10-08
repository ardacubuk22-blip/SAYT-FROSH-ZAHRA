from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import City, District, Venue
from events.models import Event
from tours.models import Agency, Tour, TourDate, TourStop

DEMO_URL = "https://demo.invalid/"


class Command(BaseCommand):
    help = "Add fake demo events and tours (to look at the website before real data exists). Use --remove to delete them."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Delete the demo records")

    def handle(self, *args, **opts):
        if opts["remove"]:
            events = Event.objects.filter(source_url__startswith=DEMO_URL).delete()[0]
            tours = Tour.objects.filter(title__startswith="[نمونه]").delete()[0]
            Agency.objects.filter(license_number="DEMO-0000").delete()
            self.stdout.write(f"Removed demo records ({events + tours} rows).")
            return

        city = City.objects.get(slug="istanbul")
        beyoglu, _ = District.objects.get_or_create(city=city, name="Beyoğlu", defaults={"name_fa": "بیاوغلو"})
        kadikoy, _ = District.objects.get_or_create(city=city, name="Kadıköy", defaults={"name_fa": "قاضی‌کوی"})
        akm, _ = Venue.objects.get_or_create(city=city, name="Atatürk Kültür Merkezi", defaults={"district": beyoglu})
        moda, _ = Venue.objects.get_or_create(city=city, name="Moda Sahnesi", defaults={"district": kadikoy})
        now = timezone.localtime()

        def event(slug, title, title_fa, desc_fa, category, days, venue, district, price=None, free=False, hours=20):
            start = (now + timedelta(days=days)).replace(hour=hours, minute=0, second=0, microsecond=0)
            Event.objects.update_or_create(
                source_url=f"{DEMO_URL}{slug}",
                defaults=dict(
                    title=title, title_fa=title_fa, description=desc_fa, description_fa=desc_fa,
                    category=category, start=start, city=city, venue=venue, district=district,
                    price_min=price, price_max=price, is_free=free, confidence=1.0,
                    status=Event.Status.PUBLISHED,
                ),
            )

        event("1", "Boğaz'da Caz Gecesi", "شب جاز کنار بسفر", "کنسرت جاز با نوازندگان مهمان در فضایی صمیمی.",
              "concert", 0, akm, beyoglu, price=450, hours=21)
        event("2", "Bir Ziyaret", "یک دیدار", "نمایشی از شهر تئاترلری استانبول، بر اساس نمایشنامه‌ای مشهور.",
              "theatre", 1, moda, kadikoy, price=300)
        event("3", "Şehrin Renkleri Sergisi", "نمایشگاه رنگ‌های شهر", "نمایشگاه نقاشی هنرمندان جوان، ورود آزاد.",
              "art_exhibition", 2, akm, beyoglu, free=True, hours=11)
        event("4", "Çocuklar için Masal Atölyesi", "کارگاه قصه برای کودکان", "کارگاه قصه‌گویی برای کودکان ۶ تا ۱۰ سال.",
              "art_workshop", 5, moda, kadikoy, free=True, hours=13)
        event("5", "Sinema Günleri", "روزهای سینما", "نمایش فیلم‌های کوتاه ترکیه.",
              "film_festival", 9, akm, beyoglu, price=120)

        agency, _ = Agency.objects.get_or_create(name="[نمونه] آژانس بسفر", license_number="DEMO-0000")
        guided, _ = Tour.objects.get_or_create(
            title="[نمونه] تور یک‌روزه‌ی استانبول قدیم",
            defaults=dict(kind="guided", city=city, agency=agency, price=1800, capacity=15, is_published=True,
                          description="بازدید از آیاصوفیه، مسجد سلطان‌احمد و بازار بزرگ با راهنمای فارسی‌زبان."),
        )
        selfg, _ = Tour.objects.get_or_create(
            title="[نمونه] تور خودگردان: موزه‌های فاتح",
            defaults=dict(kind="self_guided", city=city, is_published=True,
                          description="مسیر پیشنهادی برای بازدید مستقل؛ ساعت کاری هر مکان را قبل از رفتن ببینید."),
        )
        if not guided.stops.exists():
            TourStop.objects.create(tour=guided, order=1, name="Ayasofya", description="شروع تور با آیاصوفیه.",
                                    opening_hours="09:00–19:00")
            TourStop.objects.create(tour=guided, order=2, name="Kapalıçarşı", description="گشت در بازار بزرگ.",
                                    opening_hours="09:00–19:00", closed_days="یکشنبه‌ها")
            TourDate.objects.create(tour=guided, start_date=timezone.localdate() + timedelta(days=6))
            TourDate.objects.create(tour=guided, start_date=timezone.localdate() + timedelta(days=13))
        if not selfg.stops.exists():
            TourStop.objects.create(tour=selfg, order=1, name="İstanbul Arkeoloji Müzeleri", opening_hours="09:00–18:00",
                                    closed_days="دوشنبه‌ها", description="مجموعه‌ی آثار باستانی.")
            TourStop.objects.create(tour=selfg, order=2, name="Topkapı Sarayı", opening_hours="09:00–18:00",
                                    closed_days="سه‌شنبه‌ها", description="کاخ سلاطین عثمانی.")
        self.stdout.write(self.style.SUCCESS("Demo records added. Remove them with: python manage.py seed_demo --remove"))
