"""Conservative extraction of explicit legal-control evidence from source text.

This module identifies *candidate* legal-control statements.  It never promotes a
catalog source, never infers that a web/GIS representation is the adopted legal
instrument, and never treats provenance or an official link as legal control.
"""
from __future__ import annotations

import re
from typing import Any

_WS_RE = re.compile(r"\s+")


def _clean(value: object) -> str:
    return _WS_RE.sub(" ", str(value or "")).strip()


def _extract_adopted_map_title(text: str) -> str | None:
    patterns = (
        r'adopts?\s+the\s+(?P<title>Official\s+(?:Land\s+Use|Zoning)\s+Map(?:,?\s+entitled\s+["“][^"”]+["”])?)',
        r'(?P<title>Official\s+(?:Land\s+Use|Zoning)\s+Map(?:\s+of\s+the\s+[^.;]{1,180})?)\s+shall\s+supersede',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return _clean(match.group("title"))
    return None


def evaluate_legal_control_text(
    *,
    content: str | bytes | None,
    source_url: str | None = None,
) -> dict[str, Any]:
    """Extract explicit legal-control signals without assigning them to a target source.

    A positive result means the text contains an explicit statement about a legally
    controlling zoning/land-use map.  It does *not* mean any ArcGIS layer, PDF, or
    other representation has been proven to be that map.
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8", "ignore")
    else:
        text = str(content or "")
    normalized = _clean(text)
    if not normalized:
        return {
            "status": "LEGAL_CONTROL_NOT_ESTABLISHED",
            "legal_control_confirmed": False,
            "reason": "SOURCE_CONTENT_EMPTY",
            "source_url": source_url,
            "signals": [],
        }

    signals: list[str] = []
    adopted_title = _extract_adopted_map_title(normalized)
    if adopted_title:
        signals.append("EXPLICIT_MAP_ADOPTION")

    final_authority = bool(re.search(
        r"(?:original\s+map|official\s+(?:zoning|land\s+use)\s+map).{0,240}"
        r"(?:shall\s+be\s+used\s+as\s+the\s+final\s+authority|final\s+authority)",
        normalized,
        re.I,
    ))
    if final_authority:
        signals.append("EXPLICIT_FINAL_AUTHORITY_STATEMENT")

    amendment_required = bool(re.search(
        r"changes?.{0,220}(?:will|shall)\s+not\s+become\s+effective\s+until.{0,160}"
        r"official\s+(?:zoning|land\s+use)\s+map\s+has\s+been\s+amended",
        normalized,
        re.I,
    ))
    if amendment_required:
        signals.append("EXPLICIT_MAP_AMENDMENT_CONTROL")

    if not (adopted_title and final_authority):
        return {
            "status": "LEGAL_CONTROL_NOT_ESTABLISHED",
            "legal_control_confirmed": False,
            "reason": "EXPLICIT_CONTROLLING_INSTRUMENT_NOT_PROVEN",
            "source_url": source_url,
            "signals": signals,
            "controlling_instrument": adopted_title,
        }

    return {
        "status": "LEGAL_CONTROL_EVIDENCE_DISCOVERED",
        "legal_control_confirmed": False,
        "reason": "CONTROLLING_INSTRUMENT_IDENTIFIED_BUT_TARGET_IDENTITY_NOT_PROVEN",
        "source_url": source_url,
        "signals": signals,
        "controlling_instrument": adopted_title,
        "requires_target_identity_match": True,
    }
