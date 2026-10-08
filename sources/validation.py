"""Check AI output before it reaches the database."""

from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.utils import timezone

from events.models import Category

ISTANBUL = ZoneInfo("Europe/Istanbul")


class Invalid(Exception):
    """The page cannot become an event at all (not an event, no start date, already over)."""


def _parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if len(value) == 10:  # date only
        parsed = datetime.combine(parsed.date(), time(0, 0))
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=ISTANBUL)
    return parsed


def _parse_price(value):
    if value is None:
        return None
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        return None
    return price if price >= 0 else None


def validate_event(data, now=None):
    """Return (cleaned fields, list of problems). Problems send the record to manual review."""
    now = now or timezone.now()
    if not data.get("is_event"):
        raise Invalid("صفحه مربوط به یک رویداد مشخص نیست.")

    problems = []
    title = (data.get("title") or "").strip()
    if not title:
        raise Invalid("عنوان ندارد.")

    start = _parse_dt(data.get("start"))
    if start is None:
        raise Invalid("تاریخ شروع ندارد یا نامعتبر است.")
    end = _parse_dt(data.get("end"))
    if data.get("end") and end is None:
        problems.append("تاریخ پایان نامعتبر است.")
    if end and end < start:
        problems.append("تاریخ پایان قبل از شروع است.")
        end = None
    if (end or start) < now:
        raise Invalid("رویداد تمام شده است.")
    if start > now + timezone.timedelta(days=550):
        problems.append("تاریخ شروع بیش از حد دور است.")

    category = data.get("category")
    if category not in Category.values:
        problems.append(f"دسته‌بندی نامعتبر: {category}")
        category = Category.MUNICIPALITY

    price_min = _parse_price(data.get("price_min"))
    price_max = _parse_price(data.get("price_max"))
    if price_min is not None and price_max is not None and price_min > price_max:
        price_min, price_max = price_max, price_min
    is_free = bool(data.get("is_free"))
    if is_free and price_max:
        problems.append("هم رایگان علامت خورده و هم قیمت دارد.")

    try:
        confidence = min(max(float(data.get("confidence") or 0), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.0

    cleaned = {
        "title": title[:500],
        "description": (data.get("description") or "").strip(),
        "category": category,
        "start": start,
        "end": end,
        "venue": (data.get("venue") or "").strip()[:255],
        "district": (data.get("district") or "").strip()[:100],
        "price_min": price_min,
        "price_max": price_max,
        "currency": ((data.get("currency") or "TRY").strip().upper())[:3],
        "is_free": is_free,
        "confidence": confidence,
    }
    return cleaned, problems
