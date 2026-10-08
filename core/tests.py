from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from events.models import Event
from tours.models import Tour


class SeedDemoTests(TestCase):
    def test_add_and_remove_demo_records(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())  # running twice must not duplicate
        self.assertEqual(Event.objects.count(), 5)
        self.assertEqual(Tour.objects.count(), 2)
        call_command("seed_demo", "--remove", stdout=StringIO())
        self.assertEqual((Event.objects.count(), Tour.objects.count()), (0, 0))
