"""Conservative retrieval helpers for municipal sources.

Primary retrieval remains the existing URL. If a source explicitly publishes
alternate URLs, they may be tried in order. A single browser-like retry is also
allowed for ordinary HTTP 403 responses; no URL guessing, proxying, or access
control bypass is performed.
"""
from __future__ import annotations

from typing import Any

import httpx

BROWSER_RETRY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def retrieve_source(
    client: Any,
    url: str,
    *,
    alternate_urls: list[str] | None = None,
    referer: str | None = None,
) -> tuple[Any | None, dict[str, Any]]:
    """Retrieve a source without guessing or bypassing access controls."""
    response = client.get(url)
    attempts = [{"url": url, "status_code": response.status_code}]

    if response.status_code == 403:
        headers = dict(BROWSER_RETRY_HEADERS)
        if referer:
            headers["Referer"] = referer
        response = client.get(url, headers=headers)
        attempts.append({"url": url, "status_code": response.status_code, "mode": "browser_retry"})

    if response.status_code < 400:
        return response, {"retrieval_mode": "primary_or_browser_retry", "attempts": attempts}

    for alternate_url in alternate_urls or []:
        if not alternate_url or alternate_url == url:
            continue
        response = client.get(alternate_url)
        attempts.append({"url": alternate_url, "status_code": response.status_code, "mode": "explicit_alternate"})
        if response.status_code == 403:
            headers = dict(BROWSER_RETRY_HEADERS)
            if referer:
                headers["Referer"] = referer
            response = client.get(alternate_url, headers=headers)
            attempts.append({"url": alternate_url, "status_code": response.status_code, "mode": "explicit_alternate_browser_retry"})
        if response.status_code < 400:
            return response, {"retrieval_mode": "explicit_alternate", "attempts": attempts}

    return None, {
        "retrieval_mode": "retrieval_failed",
        "attempts": attempts,
        "status_code": response.status_code,
        "final_url": str(response.url),
    }
