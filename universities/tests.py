from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import City, District, Interaction
from universities.models import AdmissionCycle, ApprovalStatus, Program, University
from universities.search import tokens


def make_university(name="İstanbul Teknik Üniversitesi", name_fa="دانشگاه فنی استانبول", slug="itu", **kw):
    city = City.objects.get(slug="istanbul")
    return University.objects.create(
        name=name, name_fa=name_fa, slug=slug, ownership="state", city=city, **kw
    )


class SearchTests(TestCase):
    def setUp(self):
        self.itu = make_university()
        self.boun = make_university("Boğaziçi Üniversitesi", "دانشگاه بوغازیچی", "boun")
        self.arch = Program.objects.create(
            university=self.itu, name="Architecture", name_fa="معماری", level="bachelor", language="en",
            tuition_foreign=5000, currency="USD",
        )
        Program.objects.create(university=self.boun, name="Physics", name_fa="فیزیک", level="master", language="tr")

    def names(self, **params):
        response = self.client.get(reverse("universities:list"), params)
        self.assertEqual(response.status_code, 200)
        return [p.name for p in response.context["page"].object_list]

    def test_tokens_normalise_arabic_letters_and_zwnj(self):
        self.assertEqual(tokens("معماري  استانبول"), ["معماری", "استانبول"])
        self.assertEqual(tokens("کارشناسی‌ارشد"), ["کارشناسی", "ارشد"])

    def test_architecture_istanbul_finds_program(self):
        self.assertEqual(self.names(q="معماری استانبول"), ["Architecture"])
        self.assertEqual(self.names(q="معماری آنکارا"), [])

    def test_matches_university_name_and_filters(self):
        self.assertEqual(self.names(q="بوغازیچی"), ["Physics"])
        self.assertEqual(self.names(level="master"), ["Physics"])
        self.assertEqual(self.names(language="en"), ["Architecture"])
        self.assertEqual(sorted(self.names(level="nonsense", q="دانشگاه")), ["Architecture", "Physics"])

    def test_university_without_programs_still_found_by_name(self):
        make_university("Marmara Üniversitesi", "دانشگاه مرمره", "marmara")
        response = self.client.get(reverse("universities:list"), {"q": "مرمره"})
        self.assertEqual([u.slug for u in response.context["universities"]], ["marmara"])

    def test_default_page_lists_universities(self):
        response = self.client.get(reverse("universities:list"))
        self.assertContains(response, "دانشگاه فنی استانبول")
        self.assertFalse(response.context["searching"])


@override_settings(WHATSAPP_NUMBER="905550000000")
class DetailTests(TestCase):
    def setUp(self):
        self.uni = make_university(has_dormitory=True, official_url="https://itu.example/")
        self.medical = Program.objects.create(
            university=self.uni, name="Medicine", name_fa="پزشکی", level="bachelor", is_medical=True
        )
        self.cycle = AdmissionCycle.objects.create(
            program=self.medical,
            registration_start=timezone.localdate() - timedelta(days=3),
            registration_end=timezone.localdate() + timedelta(days=10),
            documents="گذرنامه", registration_url="https://apply.example/",
        )

    def test_unknown_approval_is_never_shown_as_approved(self):
        page = self.client.get(reverse("universities:detail", args=[self.uni.slug]))
        self.assertEqual(self.uni.science_ministry_status, ApprovalStatus.UNKNOWN)
        self.assertContains(page, "بررسی نشده")
        self.assertNotContains(page, "تأیید شده")
        self.assertContains(page, "ثبت‌نام باز است")
        self.assertContains(page, "https://apply.example/")

    def test_manual_approval_with_check_date_is_shown(self):
        self.uni.science_ministry_status = ApprovalStatus.APPROVED
        self.uni.science_ministry_checked = timezone.localdate()
        self.uni.save()
        self.medical.health_ministry_status = ApprovalStatus.NOT_APPROVED
        self.medical.save()
        page = self.client.get(reverse("universities:detail", args=[self.uni.slug]))
        self.assertContains(page, "تأیید شده")
        self.assertContains(page, "آخرین بررسی")
        self.assertContains(page, "تأیید وزارت بهداشت: تأیید نشده")

    def test_whatsapp_consult_and_unpublished(self):
        response = self.client.get(reverse("universities:whatsapp", args=[self.uni.slug]))
        message = parse_qs(urlsplit(response["Location"]).query)["text"][0]
        self.assertIn(self.uni.code, message)
        self.assertIn("دانشگاه فنی استانبول", message)
        self.uni.is_published = False
        self.uni.save()
        self.assertEqual(self.client.get(reverse("universities:detail", args=[self.uni.slug])).status_code, 404)

    def test_consented_visit_is_logged(self):
        self.client.post(reverse("consent"), {"choice": "yes"})
        self.client.get(reverse("universities:detail", args=[self.uni.slug]))
        self.client.get(reverse("universities:whatsapp", args=[self.uni.slug]))
        self.assertEqual(
            list(Interaction.objects.order_by("id").values_list("kind", "object_type", "object_id")),
            [("view", "university", self.uni.pk), ("whatsapp", "university", self.uni.pk)],
        )

    def test_cycle_open_status(self):
        self.assertTrue(self.cycle.is_open)
        self.cycle.registration_end = timezone.localdate() - timedelta(days=1)
        self.assertFalse(self.cycle.is_open)
        self.assertFalse(AdmissionCycle(program=self.medical).is_open)
