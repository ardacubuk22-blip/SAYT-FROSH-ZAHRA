"""Helpers shared by the public pages: WhatsApp links and consent-based anonymous logging."""

import uuid
from urllib.parse import quote

from django.conf import settings

from .models import Interaction

CONSENT_COOKIE = "td_consent"
VISITOR_COOKIE = "td_visitor"
COOKIE_AGE = 60 * 60 * 24 * 365


def whatsapp_link(message):
    return f"https://wa.me/{settings.WHATSAPP_NUMBER}?text={quote(message)}"


def booking_message(kind, code, title):
    return f"سلام، می‌خواهم {kind} زیر را رزرو کنم:\nکد: {code}\nعنوان: {title}"


def has_consent(request):
    return request.COOKIES.get(CONSENT_COOKIE) == "yes"


def log_interaction(request, kind, obj_type, obj_id):
    """Record the visit only if the visitor accepted the notice. Never raises."""
    visitor = request.COOKIES.get(VISITOR_COOKIE, "")
    if not has_consent(request) or not visitor:
        return
    try:
        uuid.UUID(visitor)
    except ValueError:
        return
    Interaction.objects.create(kind=kind, object_type=obj_type, object_id=obj_id, visitor_id=visitor)
