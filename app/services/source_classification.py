"""Classify discovered municipal sources without asserting legal control."""
from __future__ import annotations

from typing import Any
import re
from urllib.parse import urlparse


def classify_discovered_source(label: str, url: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source or {}
    text = f"{label} {url}".lower()
    host = urlparse(url).netloc.lower()

    legal_code_signal = bool(
        "ordinance" in text
        or "ecode360" in host
        or re.search(r"\b(?:municipal|city|zoning|land\s+use)\s+code\b", text)
        or re.search(r"\bcode\s+of\s+(?:the\s+)?(?:city|borough|township|town|village)\b", text)
    )
    administrative_code_signal = bool(
        re.search(r"\bcode\s+enforcement\b", text)
        or re.search(r"\bcodes?\s+department\b", text)
    )

    if legal_code_signal and not administrative_code_signal:
        role = "zoning_ordinance"
    elif "map" in text or "gis" in text or "viewer" in text or "arcgis" in host:
        role = "zoning_map"
    elif "zoning" in text or "land use" in text or "planning" in text:
        role = "zoning_administration"
    else:
        role = "municipal_zoning_source"

    municipality = str(source.get("municipality") or "").strip().lower()
    municipality_tokens = [token for token in re.split(r"\W+", municipality) if token and token not in {"city", "township", "borough", "town", "village"}]
    municipality_key = "".join(municipality_tokens)
    host_key = re.sub(r"[^a-z0-9]", "", host)
    municipal_host = (
        host.endswith(".nj.us")
        or host.endswith(".nj.gov")
        or (municipality_key and municipality_key in host_key)
    )
    authority_tier = "likely_municipal_or_state_domain" if municipal_host else "external_or_unknown_domain"

    return {
        "source_role": role,
        "authority_tier": authority_tier,
        "classification_scope": "domain_and_source_label_heuristic",
        "authoritative": False,
        "evidence_status": "DISCOVERED_CANDIDATE",
        "legal_control_confirmed": False,
        "classification_notes": [
            "Classification identifies the likely function of a discovered source.",
            "Discovery and domain classification do not establish legal control or effective zoning law.",
        ],
    }
