"""Every source has one adapter. An adapter knows where a site lists its events."""

import re
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from ..text import html_to_text


class BaseAdapter:
    city_slug = "istanbul"
    # Pages that list events; relative to the source URL.
    listing_paths = ("",)
    # Regex for the path of a single event page on this site.
    event_link_pattern = None
    # Safety limit per run.
    max_pages = 200

    def __init__(self, source):
        self.source = source

    def listing_urls(self):
        return [urljoin(self.source.url, path) for path in self.listing_paths]

    def find_event_links(self, fetcher):
        host = urlsplit(self.source.url).hostname
        pattern = re.compile(self.event_link_pattern)
        links = []
        for listing_url in self.listing_urls():
            html = fetcher.get(listing_url).text
            for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
                url = urldefrag(urljoin(listing_url, a["href"])).url
                if urlsplit(url).hostname == host and pattern.search(urlsplit(url).path) and url not in links:
                    links.append(url)
        return links[: self.max_pages]

    def page_text(self, html):
        return html_to_text(html)
