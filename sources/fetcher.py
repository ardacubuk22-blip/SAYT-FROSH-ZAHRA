"""Polite HTTP fetching: respects robots.txt, waits between requests, identifies itself."""

import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from django.conf import settings

# Ticket sellers and accommodation booking sites: we only link to them, never crawl them.
TICKET_DOMAINS = (
    "biletix.com",
    "passo.com.tr",
    "biletinial.com",
)
LODGING_DOMAINS = (
    "booking.com",
    "airbnb.com",
    "hotels.com",
    "expedia.com",
    "trivago.com",
    "agoda.com",
    "otelz.com",
    "etstur.com",
    "tatilsepeti.com",
    "jollytur.com",
)
BLOCKED_DOMAINS = TICKET_DOMAINS + LODGING_DOMAINS


class FetchNotAllowed(Exception):
    """The URL is blocked by our rules or by the site's robots.txt."""


def _host_in(url, domains):
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def is_blocked_domain(url):
    return _host_in(url, BLOCKED_DOMAINS)


def is_ticket_domain(url):
    return _host_in(url, TICKET_DOMAINS)


class PoliteFetcher:
    def __init__(self, user_agent=None, delay=None, client=None):
        self.user_agent = user_agent or settings.CRAWLER_USER_AGENT
        self.delay = settings.CRAWLER_DELAY_SECONDS if delay is None else delay
        self.client = client or httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=30,
            follow_redirects=True,
        )
        self._robots = {}
        self._last_request = {}

    def close(self):
        self.client.close()

    def _wait_turn(self, host):
        last = self._last_request.get(host)
        if last is not None:
            remaining = self.delay - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request[host] = time.monotonic()

    def _robots_for(self, url):
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        if base not in self._robots:
            parser = RobotFileParser()
            self._wait_turn(parts.netloc)
            resp = self.client.get(base + "/robots.txt")
            if resp.status_code in (401, 403):
                parser.disallow_all = True
            elif resp.status_code >= 400:
                parser.allow_all = True
            else:
                parser.parse(resp.text.splitlines())
            self._robots[base] = parser
        return self._robots[base]

    def allowed(self, url):
        if is_blocked_domain(url):
            return False
        return self._robots_for(url).can_fetch(self.user_agent, url)

    def get(self, url):
        if not self.allowed(url):
            raise FetchNotAllowed(url)
        self._wait_turn(urlsplit(url).netloc)
        resp = self.client.get(url)
        resp.raise_for_status()
        return resp
