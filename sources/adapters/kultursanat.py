"""kultursanat.istanbul — the central culture & arts calendar of İBB (Istanbul municipality).

Checked against the live site (Oct 2026): event pages look like
/etkinliklerimiz/<id>/<slug>, and the listing is paginated at /etkinliklerimiz/ara?page=N
(12 events per page).
"""

from .base import BaseAdapter


class KultursanatAdapter(BaseAdapter):
    listing_paths = ("etkinliklerimiz",) + tuple(f"etkinliklerimiz/ara?page={n}" for n in range(1, 6))
    event_link_pattern = r"^/etkinliklerimiz/\d+/[^/]+/?$"
