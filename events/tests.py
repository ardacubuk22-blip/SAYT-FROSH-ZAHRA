import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import City, Interaction
from events.models import Event
from events.views import time_window
from tours.models import Agency, Tour, TourDate, TourStop


def make_event(title, days=2, **kwargs):
    city = City.objects.get(slug="istanbul")
    defaults = dict(
        title=title, category="concert", start=timezone.now() + timedelta(days=days), city=city,
        source_url=f"https://example.test/{title.replace(' ', '-')}", status=Event.Status.PUBLISHED,
    )
    defaults.update(kwargs)
    return Event.objects.create(**defaults)


class EventListTests(TestCase):
    def titles(self, **params):
        response = self.client.get(reverse("events:list"), params)
        self.assertEqual(response.status_code, 200)
        return [e.title for e in response.context["page"].object_list]

    def test_only_published_upcoming_events_are_listed(self):
        make_event("Public")
        make_event("Hidden", status=Event.Status.NEEDS_REVIEW)
        make_event("Past", days=-3)
        self.assertEqual(self.titles(), ["Public"])

    def test_category_and_free_filters(self):
        make_event("Concert A")
        make_event("Free Expo", category="art_exhibition", is_free=True)
        self.assertEqual(self.titles(category="art_exhibition"), ["Free Expo"])
        self.assertEqual(self.titles(free="1"), ["Free Expo"])
        self.assertEqual(sorted(self.titles(category="nonsense")), ["Concert A", "Free Expo"])

    def test_time_filters(self):
        now = timezone.localtime()
        make_event("Tonight", start=now + timedelta(minutes=30))
        make_event("Next month", days=30)
        make_event("Ongoing exhibition", start=now - timedelta(days=5), end=now + timedelta(days=5))
        self.assertEqual(sorted(self.titles(time="today")), ["Ongoing exhibition", "Tonight"])
        self.assertNotIn("Next month", self.titles(time="week"))

    def test_weekend_window_is_saturday_and_sunday(self):
        wednesday = timezone.make_aware(timezone.datetime(2026, 10, 7, 12, 0))
        start, until = time_window("weekend", wednesday)
        self.assertEqual((start.date().isoformat(), start.weekday()), ("2026-10-10", 5))
        self.assertEqual(until.date().isoformat(), "2026-10-12")
        sunday = timezone.make_aware(timezone.datetime(2026, 10, 11, 12, 0))
        self.assertEqual(time_window("weekend", sunday)[0], sunday)

    def test_other_city_filter(self):
        City.objects.create(name="Ankara", name_fa="آنکارا", slug="ankara")
        make_event("Istanbul show")
        make_event("Ankara show", city=City.objects.get(slug="ankara"), source_url="https://example.test/a")
        self.assertEqual(self.titles(city="ankara"), ["Ankara show"])
        self.assertEqual(self.titles(), ["Istanbul show"])


@override_settings(WHATSAPP_NUMBER="905550000000")
class EventDetailTests(TestCase):
    def test_detail_page_and_whatsapp_link(self):
        event = make_event("Caz Gecesi", title_fa="شب جاز", ticket_url="https://www.biletix.com/x")
        page = self.client.get(reverse("events:detail", args=[event.pk]))
        self.assertContains(page, "شب جاز")
        self.assertContains(page, "رزرو از طریق واتساپ")
        self.assertContains(page, "https://www.biletix.com/x")
        self.assertContains(page, event.source_url)

        response = self.client.get(reverse("events:whatsapp", args=[event.pk]))
        self.assertEqual(response.status_code, 302)
        target = urlsplit(response["Location"])
        self.assertEqual((target.netloc, target.path), ("wa.me", "/905550000000"))
        message = parse_qs(target.query)["text"][0]
        self.assertIn(event.code, message)
        self.assertIn("شب جاز", message)

    def test_unpublished_event_is_404(self):
        event = make_event("Draft", status=Event.Status.NEEDS_REVIEW)
        self.assertEqual(self.client.get(reverse("events:detail", args=[event.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("events:whatsapp", args=[event.pk])).status_code, 404)


class ConsentLoggingTests(TestCase):
    def setUp(self):
        self.event = make_event("Logged")

    def test_nothing_is_logged_without_consent(self):
        self.client.get(reverse("events:detail", args=[self.event.pk]))
        self.client.post(reverse("consent"), {"choice": "no", "next": "/"})
        self.client.get(reverse("events:detail", args=[self.event.pk]))
        self.assertEqual(Interaction.objects.count(), 0)
        self.assertEqual(self.client.cookies["td_visitor"].value, "")  # cookie removed

    def test_view_and_click_are_logged_after_consent(self):
        response = self.client.post(reverse("consent"), {"choice": "yes", "next": "/events/"})
        self.assertEqual(response.status_code, 302)
        visitor = self.client.cookies["td_visitor"].value
        uuid.UUID(visitor)
        self.client.get(reverse("events:detail", args=[self.event.pk]))
        self.client.get(reverse("events:whatsapp", args=[self.event.pk]))
        kinds = list(Interaction.objects.order_by("id").values_list("kind", "object_type", "visitor_id"))
        self.assertEqual(kinds, [("view", "event", visitor), ("whatsapp", "event", visitor)])

    def test_consent_redirect_stays_on_our_site(self):
        response = self.client.post(reverse("consent"), {"choice": "no", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/")
        self.assertEqual(self.client.get(reverse("consent")).status_code, 405)

    def test_banner_shown_until_answered(self):
        self.assertContains(self.client.get(reverse("events:list")), "موافقم")
        self.client.post(reverse("consent"), {"choice": "no"})
        self.assertNotContains(self.client.get(reverse("events:list")), "موافقم")


class TourPageTests(TestCase):
    def setUp(self):
        city = City.objects.get(slug="istanbul")
        agency = Agency.objects.create(name="Bosphorus Tours", license_number="TURSAB-1234")
        self.tour = Tour.objects.create(
            title="تور تاریخی استانبول", city=city, agency=agency, price=1500, capacity=20, is_published=True
        )
        TourDate.objects.create(tour=self.tour, start_date=timezone.localdate() + timedelta(days=7))
        TourDate.objects.create(tour=self.tour, start_date=timezone.localdate() - timedelta(days=7))
        TourStop.objects.create(
            tour=self.tour, order=2, name="Topkapı", opening_hours="09:00–17:00", closed_days="سه‌شنبه‌ها"
        )
        TourStop.objects.create(tour=self.tour, order=1, name="Ayasofya", description="مسجد و موزه")

    def test_list_and_detail(self):
        self.assertContains(self.client.get(reverse("tours:list")), "تور تاریخی استانبول")
        page = self.client.get(reverse("tours:detail", args=[self.tour.pk]))
        self.assertContains(page, "TURSAB-1234")
        self.assertContains(page, "سه‌شنبه‌ها")
        self.assertEqual(len(page.context["dates"]), 1)  # the past date is hidden
        names = [s.name for s in page.context["stops"]]
        self.assertEqual(names, ["Ayasofya", "Topkapı"])

    def test_unpublished_tour_hidden_and_whatsapp_message(self):
        self.client.get(reverse("tours:whatsapp", args=[self.tour.pk]))  # published: fine
        response = self.client.get(reverse("tours:whatsapp", args=[self.tour.pk]))
        message = parse_qs(urlsplit(response["Location"]).query)["text"][0]
        self.assertIn(self.tour.code, message)
        self.tour.is_published = False
        self.tour.save()
        self.assertEqual(self.client.get(reverse("tours:detail", args=[self.tour.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("tours:list")), "تور تاریخی")

    def test_guided_tour_requires_agency(self):
        from django.core.exceptions import ValidationError

        tour = Tour(title="x", city=self.tour.city, kind=Tour.Kind.GUIDED)
        with self.assertRaises(ValidationError):
            tour.full_clean()
        Tour(title="x", city=self.tour.city, kind=Tour.Kind.SELF_GUIDED).full_clean()
