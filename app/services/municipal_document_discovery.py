"""Conservative discovery of explicitly published municipal ordinance documents."""
from __future__ import annotations

import re
from urllib.parse import urljoin

DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx")
DOCUMENT_URL_MARKERS = ("displayfile.aspx", "getfile.ashx", "/documents/", "/files/")
DOCUMENT_LABEL_PATTERNS = (
    re.compile(r"ordinance", re.I),
    re.compile(r"zoning\s+(?:code|ordinance|ordinances)", re.I),
    re.compile(r"chapter\s+430", re.I),
    re.compile(r"municipal\s+code", re.I),
)


def discover_explicit_municipal_documents(*, page_url: str, content: bytes) -> list[dict[str, str]]:
    """Find explicit first-party document links without synthesizing URLs.

    A link is accepted when its visible label identifies an ordinance/zoning/code
    document and its href is either a known document extension or an explicit
    municipal document endpoint. This remains one-page, one-hop discovery.
    """
    try:
        text = content.decode("utf-8", "ignore")
    except Exception:
        return []

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
    for match in pattern.finditer(text):
        href, raw_label = match.groups()
        label = re.sub(r"<[^>]+>", " ", raw_label)
        label = re.sub(r"\s+", " ", label).strip()
        if not label:
            continue
        url = urljoin(page_url, href.strip())
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        href_lower = href.lower().split("?", 1)[0]
        label_match = any(pattern.search(label) for pattern in DOCUMENT_LABEL_PATTERNS)
        endpoint_match = href_lower.endswith(DOCUMENT_EXTENSIONS) or any(
            marker in href_lower for marker in DOCUMENT_URL_MARKERS
        )
        if not (label_match and endpoint_match):
            continue
        seen.add(url)
        results.append({"label": label, "url": url})
    return results
