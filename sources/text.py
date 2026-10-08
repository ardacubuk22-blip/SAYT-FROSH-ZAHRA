"""Turn an HTML page into clean text plus a few metadata fields the AI should not guess."""

import hashlib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .fetcher import is_ticket_domain

NOISE_TAGS = ("script", "style", "noscript", "svg", "iframe", "form", "nav", "header", "footer", "aside")


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines = (line.strip() for line in root.get_text("\n").splitlines())
    text = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", text)


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page_metadata(html, page_url):
    """Image and ticket link are read from the HTML directly, not from the AI."""
    soup = BeautifulSoup(html, "html.parser")
    image = soup.find("meta", property="og:image")
    ticket_url = ""
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"])
        if href.startswith("http") and is_ticket_domain(href):
            ticket_url = href
            break
    return {
        "image_url": urljoin(page_url, image["content"]) if image and image.get("content") else "",
        "ticket_url": ticket_url,
    }
