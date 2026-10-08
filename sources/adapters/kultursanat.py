"""kultursanat.istanbul — the central culture & arts calendar of İBB (Istanbul municipality).

NOTE: listing_paths and event_link_pattern are first guesses. They must be checked
against the live site once network access to it is open, and adjusted if needed.
"""

from .base import BaseAdapter


class KultursanatAdapter(BaseAdapter):
    listing_paths = ("", "etkinlikler")
    event_link_pattern = r"^/etkinlik(ler)?/[^/]+/?$"
