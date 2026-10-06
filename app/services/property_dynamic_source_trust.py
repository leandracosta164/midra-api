"""Trust/currentness summary for MIDRA dynamic statewide intelligence.

This module never promotes evidence.  It converts the existing refresh,
official-representation, legal-control, and source metadata into an explicit
user-facing trust state so VERIFY results explain *why* they remain VERIFY.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def build_dynamic_source_trust_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    dynamic = result or {}
    zoning = dict(dynamic.get("zoning") or {})
    refresh = dict(zoning.get("refresh") or {})
    authority = dict(zoning.get("official_representation") or {})
    legal = dict(zoning.get("legal_control") or {})
    promotion = dict(zoning.get("promotion") or {})
    candidate = dict(zoning.get("candidate") or {})
    record = dict(candidate.get("record") or {})
    source = dict(record.get("source") or {})

    authority_promoted = _count(authority.get("promoted_count")) > 0 or source.get("authoritative") is True
    legal_promoted = _count(legal.get("promoted_count")) > 0 or source.get("legal_control_confirmed") is True
    promotable = promotion.get("promotable") is True and dynamic.get("dynamic_promotable") is True

    current_status = _text(source.get("current_status") or source.get("change_status"))
    last_checked_at = _text(source.get("last_checked_at") or source.get("retrieved_at"))
    content_hash = _text(source.get("content_hash") or source.get("current_content_hash"))

    if promotable and authority_promoted and legal_promoted:
        trust_state = "PROMOTABLE_EVIDENCE"
        verification_required = False
    elif authority_promoted and not legal_promoted:
        trust_state = "AUTHORITY_CONFIRMED_LEGAL_CONTROL_VERIFY"
        verification_required = True
    elif legal_promoted and not authority_promoted:
        trust_state = "LEGAL_CONTROL_PRESENT_AUTHORITY_VERIFY"
        verification_required = True
    elif refresh.get("registered") is True or refresh.get("status") == "DCA_SOURCES_DISCOVERED":
        trust_state = "SOURCE_DISCOVERED_VERIFY"
        verification_required = True
    else:
        trust_state = "SOURCE_DISCOVERY_VERIFY"
        verification_required = True

    reasons = []
    for value in (
        promotion.get("reason"),
        dynamic.get("reason"),
        None if authority_promoted else "SOURCE_AUTHORITY_NOT_CONFIRMED",
        None if legal_promoted else "LEGAL_CONTROL_NOT_CONFIRMED",
    ):
        text = _text(value)
        if text and text not in reasons:
            reasons.append(text)

    return {
        "status": "DYNAMIC_SOURCE_TRUST_SUMMARY",
        "trust_state": trust_state,
        "verification_required": verification_required,
        "source_discovery": {
            "status": refresh.get("status"),
            "registered": refresh.get("registered") is True,
            "canonical_name": refresh.get("canonical_name"),
            "discovery_source": refresh.get("discovery_source"),
        },
        "official_representation": {
            "status": authority.get("status"),
            "promoted_count": _count(authority.get("promoted_count")),
            "confirmed": authority_promoted,
        },
        "legal_control": {
            "status": legal.get("status"),
            "promoted_count": _count(legal.get("promoted_count")),
            "confirmed": legal_promoted,
        },
        "source_currentness": {
            "current_status": current_status,
            "last_checked_at": last_checked_at,
            "content_hash": content_hash,
        },
        "promotion": {
            "status": promotion.get("status"),
            "promotable": promotable,
            "reason": promotion.get("reason"),
        },
        "verification_reasons": reasons,
        "professional_boundary": {
            "definitive": False,
            "notice": (
                "Source discovery, authority, legal-control, and currentness status are evidence metadata. "
                "They do not themselves constitute engineer review, regulatory approval, or a legal determination."
            ),
        },
    }
