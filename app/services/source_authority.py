"""Evidence-only evaluation of source authority and provenance.

This layer deliberately distinguishes provenance from legal control. It may
confirm that a discovered source is plausibly municipal/state-controlled or
was listed by an authoritative discovery directory, but it never promotes a
source to legal control on heuristics alone.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _host(url: str) -> str:
    return urlparse(str(url or "").strip()).netloc.lower()


def _municipality_key(value: str) -> str:
    tokens = [
        token for token in str(value or "").lower().replace("_", " ").split()
        if token not in {"city", "township", "twp", "borough", "boro", "town", "village"}
    ]
    return "".join(tokens)


def _domain_is_municipal_or_state(url: str, municipality: str) -> bool:
    host = _host(url)
    if not host:
        return False
    if host.endswith(".nj.us") or host.endswith(".nj.gov"):
        return True
    key = _municipality_key(municipality)
    host_key = "".join(ch for ch in host if ch.isalnum())
    return bool(key and key in host_key)


def evaluate_source_authority(
    *,
    source: dict[str, Any] | None,
    municipality: str | None = None,
) -> dict[str, Any]:
    """Evaluate provenance/authority signals without asserting legal control."""
    source = source or {}
    url = str(source.get("source_url") or source.get("url") or "").strip()
    label = str(source.get("label") or "").strip()
    discovery_source = str(source.get("discovery_source") or "").strip().lower()
    authority_tier = str(source.get("authority_tier") or "").strip()
    official_link_verified = bool(source.get("municipal_official_link_verified"))
    official_page_url = str(source.get("municipal_official_page_url") or "").strip()
    official_page_verified = bool(
        official_link_verified
        and official_page_url
        and _domain_is_municipal_or_state(
            official_page_url,
            municipality or source.get("municipality") or "",
        )
    )

    signals: list[str] = []
    if discovery_source:
        signals.append(f"discovery_source:{discovery_source}")
    if authority_tier == "likely_municipal_or_state_domain":
        signals.append("catalog_domain_classification")
    if _domain_is_municipal_or_state(url, municipality or source.get("municipality") or ""):
        signals.append("municipal_or_state_domain")
    if official_link_verified:
        signals.append("municipal_official_link_verified")
    if official_page_verified:
        signals.append("municipal_official_page_verified")

    discovery_verified = discovery_source in {
        "nj_dca_zoning_information_directory",
        "nj_dca",
        "dca_zoning_information_directory",
    } or (
        "nj.gov" in _host(discovery_source)
        and "dca" in discovery_source
    )
    domain_verified = _domain_is_municipal_or_state(url, municipality or source.get("municipality") or "")

    if official_page_verified:
        status = "MUNICIPAL_OFFICIAL_LINK_VERIFIED"
        reason = "MUNICIPAL_OFFICIAL_PAGE_LINKS_SOURCE"
    elif discovery_verified and domain_verified:
        status = "PROVENANCE_AND_DOMAIN_VERIFIED"
        reason = "DCA_DISCOVERY_AND_MUNICIPAL_DOMAIN"
    elif discovery_verified:
        status = "DISCOVERY_PROVENANCE_VERIFIED"
        reason = "DCA_DISCOVERY_SOURCE"
    elif domain_verified:
        status = "MUNICIPAL_DOMAIN_VERIFIED"
        reason = "MUNICIPAL_OR_STATE_DOMAIN"
    else:
        status = "AUTHORITY_NOT_CONFIRMED"
        reason = "NO_EXPLICIT_AUTHORITY_SIGNAL"

    return {
        "status": status,
        "authority_verified": bool(discovery_verified or domain_verified or official_page_verified),
        "legal_control_confirmed": False,
        "legal_control_status": "NOT_EVALUATED",
        "reason": reason,
        "signals": signals,
        "source_url": url,
        "source_label": label,
        "municipal_official_page_url": official_page_url,
    }
