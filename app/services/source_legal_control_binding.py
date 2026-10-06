"""Strict binding of legal-control evidence to a concrete catalog/source target.

The binding step is intentionally narrower than provenance or title matching.  A
source is confirmed as the controlling instrument only when the legal-control
text itself explicitly identifies that exact target (URL or stable ArcGIS item
ID) in the controlling statement.  Labels, hostnames, discovery chains, and
similar titles are evidence candidates only and cannot establish legal control.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.services.source_legal_control import evaluate_legal_control_text

_ITEM_ID_RE = re.compile(r"^[0-9a-f]{32}$", re.I)


def _text(content: str | bytes | None) -> str:
    if isinstance(content, bytes):
        return content.decode("utf-8", "ignore")
    return str(content or "")


def _normalized_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"


def _arcgis_item_ids(source: dict[str, Any]) -> set[str]:
    values = {
        source.get("arcgis_item_id"),
        source.get("item_id"),
        source.get("webmap_id"),
    }
    for key in ("source_url", "url"):
        raw = str(source.get(key) or "").strip()
        if not raw:
            continue
        try:
            parsed = urlparse(raw)
            values.update(parse_qs(parsed.query).get("appid", []))
            values.update(parse_qs(parsed.query).get("id", []))
        except ValueError:
            continue
    return {str(v).lower() for v in values if v and _ITEM_ID_RE.fullmatch(str(v).strip())}


def _explicit_reference_match(content: str, target_source: dict[str, Any]) -> tuple[str | None, str | None]:
    # Exact URL reference is the strongest generic identity signal available.
    target_urls = {
        _normalized_url(target_source.get("source_url")),
        _normalized_url(target_source.get("url")),
    } - {""}
    lowered = content.lower()
    for url in sorted(target_urls):
        if url.lower() in lowered:
            return "EXACT_TARGET_URL_REFERENCE", url

    # ArcGIS item IDs are stable identifiers and may be cited without the full URL.
    for item_id in sorted(_arcgis_item_ids(target_source)):
        if item_id in lowered:
            return "EXACT_ARCGIS_ITEM_ID_REFERENCE", item_id
    return None, None


def bind_legal_control_to_source(
    *,
    legal_content: str | bytes | None,
    target_source: dict[str, Any] | None,
    legal_source_url: str | None = None,
) -> dict[str, Any]:
    """Bind controlling legal text to one exact target without heuristic promotion.

    Confirmation requires BOTH:
    1. explicit controlling-instrument/final-authority evidence in the legal text; and
    2. an exact URL or stable ArcGIS item-ID reference to the target in that text.

    Similar labels, municipal domains, DCA provenance, or a municipal page linking
    to a target are deliberately insufficient here.
    """
    target = dict(target_source or {})
    evidence = evaluate_legal_control_text(content=legal_content, source_url=legal_source_url)
    if evidence.get("status") != "LEGAL_CONTROL_EVIDENCE_DISCOVERED":
        return {
            "status": "LEGAL_CONTROL_TARGET_NOT_BOUND",
            "legal_control_confirmed": False,
            "reason": "CONTROLLING_LEGAL_EVIDENCE_NOT_ESTABLISHED",
            "legal_control_evidence": evidence,
            "target_source": target,
            "identity_signals": [],
        }

    signal, matched_reference = _explicit_reference_match(_text(legal_content), target)
    if signal is None:
        return {
            "status": "LEGAL_CONTROL_TARGET_NOT_BOUND",
            "legal_control_confirmed": False,
            "reason": "TARGET_IDENTITY_NOT_EXPLICITLY_REFERENCED",
            "legal_control_evidence": evidence,
            "target_source": target,
            "identity_signals": [],
        }

    return {
        "status": "LEGAL_CONTROL_TARGET_BOUND",
        "legal_control_confirmed": True,
        "reason": "CONTROLLING_TEXT_EXPLICITLY_IDENTIFIES_TARGET",
        "legal_control_evidence": evidence,
        "target_source": target,
        "identity_signals": [signal],
        "matched_reference": matched_reference,
    }
