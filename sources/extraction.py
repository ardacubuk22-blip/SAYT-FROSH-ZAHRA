"""Claude API calls: structured event extraction and Persian translation, with cost tracking."""

import json
from decimal import Decimal

import anthropic
from django.conf import settings
from django.utils import timezone

from events.models import Category

from .models import ApiUsage

# USD per million tokens (input, output). Prompts here stay under 100K tokens.
PRICES = {
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
}
BATCH_DISCOUNT = Decimal("0.5")
# Event pages are short; anything longer is almost certainly not a single event page.
MAX_PAGE_CHARS = 100_000


class ExtractionError(Exception):
    pass


class BudgetExceeded(ExtractionError):
    pass


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_event": {"type": "boolean"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "category": {"type": "string", "enum": list(Category.values)},
        "start": _nullable({"type": "string"}),
        "end": _nullable({"type": "string"}),
        "venue": _nullable({"type": "string"}),
        "district": _nullable({"type": "string"}),
        "price_min": _nullable({"type": "number"}),
        "price_max": _nullable({"type": "number"}),
        "currency": _nullable({"type": "string"}),
        "is_free": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": [
        "is_event", "title", "description", "category", "start", "end", "venue",
        "district", "price_min", "price_max", "currency", "is_free", "confidence",
    ],
    "additionalProperties": False,
}

CATEGORY_GUIDE = "\n".join(f"- {c.value}: {c.label}" for c in Category)

EXTRACTION_SYSTEM = f"""You extract event data from the text of one web page from a cultural events site in Türkiye.
Return only what the page states. Never invent dates, prices or places.

- is_event: false if the page is not about one specific event (e.g. a list page, news, or an error page).
- title, description: in the page's original language. Description: 1-3 factual sentences.
- category: exactly one of these keys:
{CATEGORY_GUIDE}
- start, end: local Istanbul time as "YYYY-MM-DDTHH:MM" (or "YYYY-MM-DD" if no time is given). null if unknown.
  If the event has several sessions, use the first upcoming session as start and the last as end.
- venue: the venue name as written on the page. district: the Istanbul district (ilçe), if stated.
- price_min, price_max, currency (ISO code such as TRY): only if stated. is_free: true only if the page says it is free (ücretsiz).
- confidence: 0 to 1, how sure you are that every field above is correct and complete."""

TRANSLATION_SCHEMA = {
    "type": "object",
    "properties": {"title_fa": {"type": "string"}, "description_fa": {"type": "string"}},
    "required": ["title_fa", "description_fa"],
    "additionalProperties": False,
}

TRANSLATION_SYSTEM = """Translate the event title and description into natural, fluent Persian for Iranian visitors to Istanbul.
Keep names of venues, artists and works in their original Latin spelling. Do not add information."""


def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise ExtractionError("ANTHROPIC_API_KEY در فایل .env تنظیم نشده است.")
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _check_budget():
    spent = ApiUsage.month_total()
    if spent >= Decimal(str(settings.MONTHLY_API_BUDGET_USD)):
        raise BudgetExceeded(f"سقف هزینه‌ی ماهانه ({spent} دلار) پر شده است.")


def record_usage(usage, model, purpose, source_url="", is_batch=False):
    input_price, output_price = PRICES.get(model, (Decimal("0"), Decimal("0")))
    input_tokens = (
        usage.input_tokens
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        + (getattr(usage, "cache_read_input_tokens", 0) or 0)
    )
    cost = (input_tokens * input_price + usage.output_tokens * output_price) / Decimal(1_000_000)
    if is_batch:
        cost *= BATCH_DISCOUNT
    return ApiUsage.objects.create(
        model=model,
        purpose=purpose,
        is_batch=is_batch,
        input_tokens=input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=cost,
        source_url=source_url,
    )


def _structured_call(system, user_content, schema, purpose, source_url=""):
    _check_budget()
    model = settings.EXTRACTION_MODEL
    response = _client().messages.create(
        model=model,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
    )
    record_usage(response.usage, model, purpose, source_url)
    if response.stop_reason != "end_turn":
        raise ExtractionError(f"پاسخ ناقص از API (stop_reason={response.stop_reason})")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def extract_event(page_text, page_url):
    if len(page_text) > MAX_PAGE_CHARS:
        raise ExtractionError(f"صفحه بیش از حد طولانی است ({len(page_text)} کاراکتر).")
    today = timezone.localdate().isoformat()
    user = f"Page URL: {page_url}\nToday's date: {today}\n\n<page>\n{page_text}\n</page>"
    return _structured_call(EXTRACTION_SYSTEM, user, EVENT_SCHEMA, ApiUsage.Purpose.EXTRACTION, page_url)


def translate_event(title, description, source_url=""):
    user = json.dumps({"title": title, "description": description}, ensure_ascii=False)
    return _structured_call(TRANSLATION_SYSTEM, user, TRANSLATION_SCHEMA, ApiUsage.Purpose.TRANSLATION, source_url)
