"""İBB Şehir Tiyatroları — plays are listed at /oyunlar, each play page has its schedule.

Checked against the live site (Oct 2026): static HTML, dates and stages are in the page text.
Use the host without "www": the www address returns a proxy error.
"""

from .base import BaseAdapter


class SehirTiyatrolariAdapter(BaseAdapter):
    listing_paths = ("oyunlar",)
    event_link_pattern = r"^/oyun/[^/]+/?$"
