from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import City
from events.models import Event, EventChange
from sources import extraction
from sources.fetcher import FetchNotAllowed, is_blocked_domain
from sources.models import ApiUsage, PageSnapshot, Source
from sources.pipeline import run_source, translate_published
from sources.text import html_to_text, page_metadata
from sources.validation import Invalid, validate_event

LISTING = """<html><body><nav><a href="/hakkimizda">About</a></nav><main>
<a href="/etkinlik/caz-gecesi">Caz Gecesi</a>
<a href="/etkinlik/resim-sergisi">Resim Sergisi</a>
<a href="https://www.biletix.com/x">Biletix</a>
</main></body></html>"""


def event_page(title, extra=""):
    return f"""<html><head><meta property="og:image" content="/img/{title}.jpg"></head><body>
<header>Menu</header><main><h1>{title}</h1><p>{extra}</p>
<a href="https://www.biletix.com/etkinlik/123">Bilet al</a></main><script>var x=1;</script></body></html>"""


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        if is_blocked_domain(url):
            raise FetchNotAllowed(url)
        return SimpleNamespace(text=self.pages[url])

    def close(self):
        pass


def ai_result(title, days=10, confidence=0.95, price=250, **extra):
    start = (timezone.localtime() + timedelta(days=days)).strftime("%Y-%m-%dT20:00")
    return {
        "is_event": True, "title": title, "description": f"{title} açıklama", "category": "concert",
        "start": start, "end": None, "venue": "Harbiye Açıkhava", "district": "Şişli",
        "price_min": price, "price_max": price, "currency": "TRY", "is_free": False,
        "confidence": confidence, **extra,
    }


class PipelineTests(TestCase):
    def setUp(self):
        self.source = Source.objects.get(adapter="kultursanat")
        base = "https://kultursanat.istanbul/"
        self.pages = {
            base: LISTING,
            base + "etkinlikler": "<html><body></body></html>",
            base + "etkinlik/caz-gecesi": event_page("Caz Gecesi"),
            base + "etkinlik/resim-sergisi": event_page("Resim Sergisi"),
        }
        self.results = {
            base + "etkinlik/caz-gecesi": ai_result("Caz Gecesi"),
            base + "etkinlik/resim-sergisi": ai_result("Resim Sergisi", confidence=0.4),
        }
        self.extract = mock.patch.object(extraction, "extract_event", side_effect=lambda text, url: self.results[url])
        self.extract_mock = self.extract.start()
        self.addCleanup(self.extract.stop)

    def test_full_run_publishes_and_queues(self):
        run = run_source(self.source, fetcher=FakeFetcher(self.pages))

        self.assertEqual(run.links_found, 2)
        self.assertEqual(run.created, 2)
        self.assertEqual(run.sent_to_review, 1)
        caz = Event.objects.get(title="Caz Gecesi")
        self.assertEqual(caz.status, Event.Status.PUBLISHED)
        self.assertEqual(caz.venue.name, "Harbiye Açıkhava")
        self.assertEqual(caz.district.name, "Şişli")
        self.assertEqual(caz.city.slug, "istanbul")
        self.assertEqual(caz.image_url, "https://kultursanat.istanbul/img/Caz Gecesi.jpg")
        self.assertTrue(caz.ticket_url.startswith("https://www.biletix.com/"))
        self.assertEqual(Event.objects.get(title="Resim Sergisi").status, Event.Status.NEEDS_REVIEW)
        self.source.refresh_from_db()
        self.assertIsNotNone(self.source.last_success)
        self.assertFalse(self.source.needs_attention)

    def test_unchanged_page_skips_ai(self):
        run_source(self.source, fetcher=FakeFetcher(self.pages))
        self.extract_mock.reset_mock()

        run = run_source(self.source, fetcher=FakeFetcher(self.pages))

        self.assertEqual(run.unchanged, 2)
        self.extract_mock.assert_not_called()

    def test_price_change_is_recorded_in_history(self):
        run_source(self.source, fetcher=FakeFetcher(self.pages))
        url = "https://kultursanat.istanbul/etkinlik/caz-gecesi"
        self.pages[url] = event_page("Caz Gecesi", extra="Yeni fiyat")
        self.results[url] = ai_result("Caz Gecesi", price=300)

        run = run_source(self.source, fetcher=FakeFetcher(self.pages))

        self.assertEqual(run.updated, 1)
        change = EventChange.objects.get(field="price_min")
        self.assertEqual((change.old_value, change.new_value), ("250.00", "300"))

    def test_zero_results_flags_source(self):
        self.pages["https://kultursanat.istanbul/"] = "<html><body>bakımda</body></html>"
        run_source(self.source, fetcher=FakeFetcher(self.pages))
        self.source.refresh_from_db()
        self.assertTrue(self.source.needs_attention)

    def test_ticket_sites_are_never_fetched(self):
        fetcher = FakeFetcher(self.pages)
        run_source(self.source, fetcher=fetcher)
        self.assertFalse(any("biletix" in url for url in fetcher.requested))


class ValidationTests(TestCase):
    def test_past_event_is_invalid(self):
        with self.assertRaises(Invalid):
            validate_event(ai_result("Eski", days=-3))

    def test_not_an_event(self):
        with self.assertRaises(Invalid):
            validate_event({**ai_result("Liste"), "is_event": False})

    def test_unknown_category_goes_to_review(self):
        _, problems = validate_event(ai_result("X", category="party"))
        self.assertTrue(problems)

    def test_free_with_price_goes_to_review(self):
        _, problems = validate_event(ai_result("X", is_free=True))
        self.assertTrue(problems)


class TextTests(TestCase):
    def test_noise_is_removed(self):
        text = html_to_text(event_page("Konser"))
        self.assertIn("Konser", text)
        self.assertNotIn("Menu", text)
        self.assertNotIn("var x", text)

    def test_metadata(self):
        meta = page_metadata(event_page("A"), "https://kultursanat.istanbul/etkinlik/a")
        self.assertEqual(meta["image_url"], "https://kultursanat.istanbul/img/A.jpg")


class CostTests(TestCase):
    def test_usage_cost(self):
        usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000)
        row = extraction.record_usage(usage, "claude-haiku-5-5", ApiUsage.Purpose.EXTRACTION)
        self.assertEqual(float(row.cost_usd), 0.60)
        self.assertEqual(float(ApiUsage.month_total()), 0.60)

    @override_settings(MONTHLY_API_BUDGET_USD=0.5)
    def test_budget_stops_calls(self):
        extraction.record_usage(SimpleNamespace(input_tokens=10_000_000, output_tokens=0),
                                "claude-haiku-5-5", ApiUsage.Purpose.EXTRACTION)
        with self.assertRaises(extraction.BudgetExceeded):
            extraction.extract_event("text", "https://x")


class TranslationAndPageTests(TestCase):
    def test_translation_only_for_published(self):
        city = City.objects.get(slug="istanbul")
        for title, status in [("Yayında", Event.Status.PUBLISHED), ("İncelemede", Event.Status.NEEDS_REVIEW)]:
            Event.objects.create(title=title, category="concert", start=timezone.now() + timedelta(days=2),
                                 city=city, source_url=f"https://x/{title}", status=status)
        with mock.patch.object(extraction, "translate_event",
                               return_value={"title_fa": "عنوان", "description_fa": "توضیح"}) as tr:
            self.assertEqual(translate_published(), 1)
            tr.assert_called_once()

        response = self.client.get(reverse("events:list"))
        self.assertContains(response, "عنوان")
        self.assertNotContains(response, "İncelemede")
        self.assertContains(response, 'dir="rtl"')
