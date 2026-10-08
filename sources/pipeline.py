"""One run of one source:

listing page -> event links -> fetch each page -> clean text -> compare content_hash
-> (unchanged: only update last_checked, no AI) -> AI extraction -> validation
-> low confidence or problems: review queue, otherwise publish
-> Persian translation only for published events.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import City, District, Venue
from events.models import Event, EventChange

from . import extraction
from .adapters import get_adapter
from .dedup import find_duplicate
from .fetcher import PoliteFetcher
from .models import PageSnapshot, SourceRun
from .text import content_hash, page_metadata
from .validation import Invalid, validate_event

logger = logging.getLogger(__name__)


def run_source(source, fetcher=None, limit=None):
    run = SourceRun.objects.create(source=source)
    own_fetcher = fetcher is None
    fetcher = fetcher or PoliteFetcher()
    try:
        adapter = get_adapter(source)
        links = adapter.find_event_links(fetcher)
        if limit:
            links = links[:limit]
        run.links_found = len(links)
        for url in links:
            try:
                process_page(source, adapter, fetcher, url, run)
            except extraction.BudgetExceeded as exc:
                run.error = str(exc)
                break
            except Exception as exc:
                logger.exception("Failed to process %s", url)
                run.failed += 1
                run.error = f"{url}: {exc}"
    except Exception as exc:
        logger.exception("Source %s failed", source)
        run.error = str(exc)
    finally:
        if own_fetcher:
            fetcher.close()

    now = timezone.now()
    run.finished_at = now
    run.save()
    source.last_run = now
    source.items_found_last_run = run.links_found
    source.last_error = run.error
    if run.links_found and not run.error:
        source.last_success = now
    source.save()
    return run


def process_page(source, adapter, fetcher, url, run):
    now = timezone.now()
    html = fetcher.get(url).text
    text = adapter.page_text(html)
    page_hash = content_hash(text)

    snapshot = PageSnapshot.objects.filter(url=url).first()
    if snapshot and snapshot.content_hash == page_hash:
        snapshot.last_checked = now
        snapshot.save(update_fields=["last_checked"])
        Event.objects.filter(source_url=url).update(last_checked=now)
        run.unchanged += 1
        return

    data = extraction.extract_event(text, url)
    _save_snapshot(source, url, page_hash, now)
    try:
        cleaned, problems = validate_event(data, now)
    except Invalid as exc:
        logger.info("Skipping %s: %s", url, exc)
        return

    cleaned.update(page_metadata(html, url))
    city = City.objects.get(slug=adapter.city_slug)
    event, created = _upsert_event(source, url, city, cleaned, page_hash, now)

    if created:
        run.created += 1
    else:
        run.updated += 1

    duplicate = find_duplicate(event) if event.status != Event.Status.REJECTED else None
    if duplicate:
        event.status = Event.Status.DUPLICATE
        event.duplicate_of = duplicate
        event.review_reason = f"تکراری با {duplicate.code}: {duplicate.title}"
        event.save(update_fields=["status", "duplicate_of", "review_reason"])
        run.duplicates += 1
        return

    needs_review = problems or cleaned["confidence"] < settings.REVIEW_CONFIDENCE_THRESHOLD
    if event.status != Event.Status.REJECTED:
        event.status = Event.Status.NEEDS_REVIEW if needs_review else Event.Status.PUBLISHED
        event.duplicate_of = None
        event.review_reason = "\n".join(problems) or (
            f"اطمینان پایین ({cleaned['confidence']:.2f})" if needs_review else ""
        )
        event.save(update_fields=["status", "review_reason", "duplicate_of"])

    if event.status == Event.Status.NEEDS_REVIEW:
        run.sent_to_review += 1


def _save_snapshot(source, url, page_hash, now):
    PageSnapshot.objects.update_or_create(
        url=url,
        defaults={"source": source, "content_hash": page_hash, "last_checked": now, "last_changed": now},
    )


@transaction.atomic
def _upsert_event(source, url, city, cleaned, page_hash, now):
    district = None
    if cleaned["district"]:
        district, _ = District.objects.get_or_create(city=city, name=cleaned["district"])
    venue = None
    if cleaned["venue"]:
        venue, _ = Venue.objects.get_or_create(city=city, name=cleaned["venue"], defaults={"district": district})

    fields = {
        k: cleaned[k]
        for k in (
            "title", "description", "category", "start", "end", "price_min", "price_max",
            "currency", "is_free", "confidence", "image_url", "ticket_url",
        )
    }
    fields.update(city=city, district=district, venue=venue, source=source, content_hash=page_hash,
                  last_checked=now, last_updated=now)

    event = Event.objects.filter(source_url=url).first()
    if event is None:
        return Event.objects.create(source_url=url, **fields), True

    for field in EventChange.TRACKED_FIELDS:
        old, new = getattr(event, field), fields[field]
        if old != new:
            EventChange.objects.create(event=event, field=field, old_value=_fmt(old), new_value=_fmt(new))
    if fields["title"] != event.title or fields["description"] != event.description:
        # Source text changed: the Persian translation must be redone.
        event.title_fa = ""
        event.description_fa = ""
    for key, value in fields.items():
        setattr(event, key, value)
    event.save()
    return event, False


def _fmt(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")
    return str(value)


def translate_published(limit=200):
    """Translate published events that have no Persian title yet. Returns how many were translated."""
    count = 0
    pending = Event.objects.filter(status=Event.Status.PUBLISHED, title_fa="")[:limit]
    for event in pending:
        try:
            result = extraction.translate_event(event.title, event.description, event.source_url)
        except extraction.BudgetExceeded:
            break
        except Exception:
            logger.exception("Translation failed for %s", event.source_url)
            continue
        event.title_fa = result["title_fa"].strip()
        event.description_fa = result["description_fa"].strip()
        event.save(update_fields=["title_fa", "description_fa"])
        count += 1
    return count
