from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from events.models import Event
from tours.models import Tour
from universities.models import University


class SeedDemoTests(TestCase):
    def test_add_and_remove_demo_records(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())  # running twice must not duplicate
        self.assertEqual(Event.objects.count(), 5)
        self.assertEqual(Tour.objects.count(), 2)
        self.assertEqual(University.objects.count(), 2)
        call_command("seed_demo", "--remove", stdout=StringIO())
        self.assertEqual((Event.objects.count(), Tour.objects.count(), University.objects.count()), (0, 0, 0))


class HealthCheckTests(TestCase):
    def test_healthz_answers_ok(self):
        response = self.client.get("/healthz/")
        self.assertEqual((response.status_code, response.content), (200, b"ok"))


class ProductionSettingsTests(TestCase):
    def _load(self, **env):
        import os
        import subprocess
        import sys

        from django.conf import settings

        full_env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        full_env.update(DJANGO_SETTINGS_MODULE="turkiye_discover.settings", **env)
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup(); from django.conf import settings; print(settings.DEBUG)"],
            capture_output=True, text=True, env=full_env, cwd=settings.BASE_DIR,
        )

    def test_server_refuses_to_start_with_placeholder_secret(self):
        result = self._load(DJANGO_DEBUG="False", DJANGO_SECRET_KEY="change-me")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_server_starts_with_real_secret(self):
        result = self._load(DJANGO_DEBUG="False", DJANGO_SECRET_KEY="x" * 50)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")
