"""Optional authenticated eCode360 retrieval for municipal legal sources.

The public eCode360 pages can return HTTP 403 to ordinary server-side clients.
When a municipality has provided an eCode360 API key/secret, this adapter can
retrieve the code structure and chapter content through the documented API.
It never guesses a municipality/customer ID: the customer ID must be present
in an explicitly discovered eCode360 URL such as /PE0514.
"""
from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

ECODE_API_BASE = "https://api.ecode360.com/v1"
_CUSTOMER_RE = re.compile(r"^https?://(?:www\.)?ecode360\.com/([A-Za-z0-9]+)(?:/|$)", re.I)


def extract_ecode_customer_id(url: str) -> str | None:
    match = _CUSTOMER_RE.match(str(url or "").strip())
    return match.group(1) if match else None


def _headers(api_key: str, api_secret: str) -> dict[str, str]:
    return {"api-key": api_key, "api-secret": api_secret, "Accept": "application/json"}


def _walk(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _find_chapter_guid(toc: dict[str, Any], chapter_number: str) -> str | None:
    wanted = str(chapter_number).strip().lower()
    for node in _walk(toc):
        if str(node.get("type", "")).lower() != "chapter":
            continue
        number = str(node.get("number", "")).replace("§", "").strip().lower()
        title = str(node.get("title", "")).lower()
        if number == wanted or number.lstrip("0") == wanted.lstrip("0"):
            return str(node.get("guid")) if node.get("guid") else None
        if number.startswith("ch ") and number[3:].strip() == wanted:
            return str(node.get("guid")) if node.get("guid") else None
        if wanted and wanted in title and node.get("guid"):
            return str(node["guid"])
    return None


def _flatten_content(node: Any) -> str:
    parts: list[str] = []
    if not isinstance(node, dict):
        return ""
    number = str(node.get("number") or "").strip()
    title = str(node.get("title") or "").strip()
    content = str(node.get("content") or "").strip()
    if number or title:
        parts.append(" ".join(x for x in (number, title) if x))
    if content:
        parts.append(content)
    for child in node.get("children") or []:
        child_text = _flatten_content(child)
        if child_text:
            parts.append(child_text)
    return "\n".join(parts)


def _candidate_chapters(toc: dict[str, Any]) -> list[tuple[str, str, str]]:
    keywords = ("zoning", "land use", "development", "planning", "subdivision")
    found: list[tuple[str, str, str]] = []
    for node in _walk(toc):
        if str(node.get("type", "")).lower() != "chapter" or not node.get("guid"):
            continue
        title = str(node.get("title") or "")
        number = str(node.get("number") or "")
        haystack = f"{number} {title}".lower()
        if any(keyword in haystack for keyword in keywords):
            found.append((str(node["guid"]), number, title))
    return found


def retrieve_ecode_zoning_content(
    client: Any,
    *,
    source_url: str,
    api_key: str | None,
    api_secret: str | None,
) -> tuple[Any | None, dict[str, Any]]:
    """Retrieve explicitly hosted zoning/land-use chapters through eCode API."""
    customer = extract_ecode_customer_id(source_url)
    if not customer:
        return None, {"retrieval_mode": "ecode_api_unavailable", "reason": "CUSTOMER_ID_NOT_EXPLICIT"}
    if not api_key or not api_secret:
        return None, {"retrieval_mode": "ecode_api_unavailable", "reason": "API_CREDENTIALS_NOT_CONFIGURED", "customer": customer}

    headers = _headers(api_key, api_secret)
    toc_url = f"{ECODE_API_BASE}/customer/{customer}/code/toc"
    toc_response = client.get(toc_url, headers=headers)
    attempts = [{"url": toc_url, "status_code": toc_response.status_code}]
    if toc_response.status_code >= 400:
        return None, {"retrieval_mode": "ecode_api_failed", "customer": customer, "attempts": attempts, "status_code": toc_response.status_code}

    candidates = _candidate_chapters(toc_response.json())
    if not candidates:
        return None, {"retrieval_mode": "ecode_api_failed", "customer": customer, "attempts": attempts, "reason": "ZONING_CHAPTER_NOT_FOUND"}

    chapter_text: list[str] = []
    retrieved_chapters: list[dict[str, str]] = []
    for guid, number, title in candidates[:5]:
        content_url = f"{ECODE_API_BASE}/customer/{customer}/code/content/{guid}"
        content_response = client.get(content_url, headers=headers)
        attempts.append({"url": content_url, "status_code": content_response.status_code})
        if content_response.status_code >= 400:
            continue
        payload = content_response.json()
        content = _flatten_content(payload).strip()
        if content:
            chapter_text.append(content)
            retrieved_chapters.append({"guid": guid, "number": number, "title": title})

    if not chapter_text:
        return None, {"retrieval_mode": "ecode_api_failed", "customer": customer, "attempts": attempts, "reason": "ZONING_CHAPTER_CONTENT_UNAVAILABLE"}

    content = "\n\n".join(chapter_text)
    response = SimpleNamespace(
        status_code=200,
        url=source_url,
        content=content.encode("utf-8"),
        headers={"content-type": "text/plain; charset=utf-8"},
    )
    return response, {
        "retrieval_mode": "ecode_api",
        "customer": customer,
        "retrieved_chapters": retrieved_chapters,
        "attempts": attempts,
    }
