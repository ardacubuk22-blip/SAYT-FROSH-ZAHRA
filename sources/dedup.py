"""Find the same event listed twice (same day + same place + similar title), e.g. on two sources."""

import re
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher

from django.db.models import Q
from django.utils import timezone

from events.models import Event

SIMILARITY = 0.8


def normalize_title(title):
    # Turkish dotted/dotless i do not survive str.lower() cleanly, so fold them first.
    title = title.replace("İ", "i").replace("I", "i").replace("ı", "i")
    title = unicodedata.normalize("NFKD", title.lower())
    title = "".join(c for c in title if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def similar(a, b):
    a, b = normalize_title(a), normalize_title(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return min(len(a), len(b)) >= 6
    return SequenceMatcher(None, a, b).ratio() >= SIMILARITY


def find_duplicate(event):
    """Return an older event that is the same as this one, or None. The older record is the one we keep."""
    day_start = timezone.localtime(event.start).replace(hour=0, minute=0, second=0, microsecond=0)
    candidates = (
        Event.objects.filter(city=event.city, start__gte=day_start, start__lt=day_start + timedelta(days=1))
        .filter(pk__lt=event.pk)
        .exclude(status__in=[Event.Status.DUPLICATE, Event.Status.REJECTED])
    )
    if event.venue_id:
        candidates = candidates.filter(Q(venue_id=event.venue_id) | Q(venue__isnull=True))
    for other in candidates:
        if similar(event.title, other.title):
            return other
    return None
