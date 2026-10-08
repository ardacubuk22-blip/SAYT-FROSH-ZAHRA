"""Atatürk Kültür Merkezi — event pages look like /tr/etkinlik/<slug>, linked from the home page.

NOTE: the site is a Next.js app and the event data (date, venue) is loaded by JavaScript, so the
plain HTML of an event page has almost no text. This adapter stays inactive until we find a way
to read the data (see CLAUDE.md).
"""

from .base import BaseAdapter


class AkmAdapter(BaseAdapter):
    listing_paths = ("tr/anasayfa",)
    event_link_pattern = r"^/tr/etkinlik/[^/]+/?$"
