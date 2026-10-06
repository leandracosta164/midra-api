"""Bounded discovery of zoning-specific pages on an official municipal website.

This service does not search the public web and does not infer legal control.  Starting
from an already-discovered municipal URL, it may inspect the same site's root page and
return only explicit same-host links whose visible label or URL identifies zoning.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urljoin, urlparse, urlunparse

_ANCHOR_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_ZONING_RE = re.compile(r"\bzoning\b", re.I)
_NON_PAGE_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".svg",
)


def _municipality_key(value: object) -> str:
    tokens = [
        token for token in re.split(r"\W+", str(value or "").lower())
        if token and token not in {"city", "township", "twp", "borough", "boro", "town", "village", "of"}
    ]
    return "".join(tokens)


def _host_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def is_official_municipal_site(url: object, municipality: object) -> bool:
    """Conservatively recognize a municipal website from municipality identity.

    State ``nj.gov`` pages are deliberately not accepted merely because they are
    governmental.  A municipality-specific hostname or a ``.nj.us`` municipal host
    is required.
    """
    try:
        host = urlparse(str(url or "").strip()).netloc.lower().split(":", 1)[0]
    except ValueError:
        return False
    if not host:
        return False
    if host.endswith(".nj.us"):
        return True
    key = _municipality_key(municipality)
    return bool(key and key in _host_key(host))


def municipal_site_root(url: object, municipality: object) -> str | None:
    """Return the HTTP(S) origin for a verified municipal seed URL."""
    raw = str(url or "").strip()
    if not is_official_municipal_site(raw, municipality):
        return None
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), "/", "", "", ""))


def discover_zoning_page_links(*, page_url: str, content: bytes) -> list[dict[str, str]]:
    """Return explicit same-host HTML-page links that identify zoning.

    The function never synthesizes a zoning URL.  It only follows links actually
    published on the supplied municipal page and excludes documents/external apps;
    those remain handled by the existing document and zoning-target pipelines.
    """
    try:
        text = content.decode("utf-8", "ignore")
        page = urlparse(page_url)
    except (AttributeError, ValueError):
        return []
    page_host = page.netloc.lower()
    if not page_host:
        return []

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _ANCHOR_RE.finditer(text):
        href, raw_label = match.groups()
        label = _SPACE_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", raw_label))).strip()
        try:
            url = urljoin(page_url, html.unescape(href).strip())
            parsed = urlparse(url)
        except ValueError:
            continue
        if parsed.scheme.lower() not in {"http", "https"} or parsed.netloc.lower() != page_host:
            continue
        path_lower = parsed.path.lower()
        if path_lower.endswith(_NON_PAGE_EXTENSIONS):
            continue
        context = f"{label} {html.unescape(href)}"
        if not _ZONING_RE.search(context):
            continue
        normalized = urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", "", parsed.query, ""))
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append({"label": label or "Zoning", "url": normalized})
    return results
