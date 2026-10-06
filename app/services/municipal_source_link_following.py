"""Conservatively discover first-party ordinance/code links from retrieved HTML."""
from __future__ import annotations

import re
from urllib.parse import urljoin

LINK_LABEL_PATTERNS = (
    re.compile(r"city\s+ordinances?", re.I),
    re.compile(r"municipal\s+ordinances?", re.I),
    re.compile(r"zoning\s+(?:code|ordinance|ordinances)", re.I),
    re.compile(r"ecode", re.I),
    re.compile(r"municipal\s+code", re.I),
    re.compile(r"city\s+code", re.I),
    re.compile(r"local\s+(?:laws?|ordinances?)(?:\s*&\s*ordinances?)?", re.I),
)

DOCUMENT_LABEL_PATTERNS = (
    re.compile(r"ordinance", re.I),
    re.compile(r"zoning\s+(?:code|ordinance)", re.I),
    re.compile(r"chapter\s+430", re.I),
    re.compile(r"municipal\s+code", re.I),
)
DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx")


def discover_ordinance_links(*, page_url: str, content: bytes) -> list[dict[str, str]]:
    """Return explicit ordinance/code links found in a retrieved HTML page."""
    try:
        text = content.decode("utf-8", "ignore")
    except Exception:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.I | re.S):
        href, raw_label = match.groups()
        label = re.sub(r"<[^>]+>", " ", raw_label)
        label = re.sub(r"\s+", " ", label).strip()
        if not label or not any(pattern.search(label) for pattern in LINK_LABEL_PATTERNS):
            continue
        url = urljoin(page_url, href.strip())
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        results.append({"label": label, "url": url})
    return results


def discover_explicit_document_links(*, page_url: str, content: bytes) -> list[dict[str, str]]:
    """Return explicit first-party ordinance/document links from retrieved HTML.

    This is deliberately one-hop and only returns links that are actually
    present in the page. It never synthesizes document URLs.
    """
    try:
        text = content.decode("utf-8", "ignore")
    except Exception:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.I | re.S):
        href, raw_label = match.groups()
        label = re.sub(r"<[^>]+>", " ", raw_label)
        label = re.sub(r"\s+", " ", label).strip()
        url = urljoin(page_url, href.strip())
        if not label or not url.startswith(("http://", "https://")) or url in seen:
            continue
        href_lower = href.lower().split("?", 1)[0]
        label_match = any(pattern.search(label) for pattern in DOCUMENT_LABEL_PATTERNS)
        extension_match = href_lower.endswith(DOCUMENT_EXTENSIONS)
        if not (label_match and extension_match):
            continue
        seen.add(url)
        results.append({"label": label, "url": url})
    return results
