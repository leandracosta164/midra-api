"""Bounded discovery of explicit municipal tax-map links.

The caller must supply HTML from an already-verified municipal page.  This
module never searches the web, guesses a tax-map URL, or infers a sheet from a
block/lot number.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

_TAX_MAP_LABEL = re.compile(r"\btax\s*maps?\b", re.I)
_TAX_MAP_URL = re.compile(r"(?:tax[-_]?maps?|taxmaps)(?:[/_.-]|$)", re.I)
_SHEET_RE = re.compile(r"\b(?:tax\s*map\s*)?sheet\s*(?:no\.?|number|#)?\s*([A-Za-z0-9.-]+)\b", re.I)

# These are about standards/processes for preparing tax maps, not the
# municipality's actual tax-map set.
_EXCLUDED_CONTEXT = re.compile(
    r"\b(?:regulations?|standards?|specifications?|submittal|submission|"
    r"template|procedures?|instructions?|faq|frequently\s+asked|cad\s+standards?)\b",
    re.I,
)


def _clean_label(raw: str) -> str:
    return _SPACE_RE.sub(" ", _TAG_RE.sub(" ", raw or "")).strip()


def _explicit_sheet(label: str, url: str) -> str | None:
    for value in (label, url):
        match = _SHEET_RE.search(value or "")
        if match:
            return match.group(1).rstrip("._-/")
    return None


def discover_explicit_tax_map_links(
    *,
    page_url: str,
    content: bytes,
) -> list[dict[str, str | None]]:
    """Return explicit tax-map links present on one verified municipal page."""
    try:
        text = content.decode("utf-8", "ignore")
    except Exception:
        return []

    results: list[dict[str, str | None]] = []
    seen: set[str] = set()

    for match in _LINK_RE.finditer(text):
        href, raw_label = match.groups()
        label = _clean_label(raw_label)
        url = urljoin(page_url, (href or "").strip())

        if not label or not url.startswith(("http://", "https://")) or url in seen:
            continue

        evidence_text = f"{label} {href}"
        if _EXCLUDED_CONTEXT.search(evidence_text):
            continue

        if not (_TAX_MAP_LABEL.search(label) or _TAX_MAP_URL.search(href or "")):
            continue

        seen.add(url)
        sheet = _explicit_sheet(label, url)
        results.append({
            "label": label,
            "url": url,
            "tax_map_sheet": sheet,
            "source_role": "tax_map",
        })

    return results
