"""Generic adapter for authoritative parcel-specific zoning evidence.

This layer deliberately accepts evidence, not assumptions.  A future municipal
GIS/ordinance extractor can translate its result into this small contract and
use the same validation path without adding municipality-specific branches.
"""

from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip()


def _norm(value: object) -> str:
    text = " ".join(_text(value).lower().split())
    aliases = {
        "howell": "howell township",
        "howell twp": "howell township",
        "howell township": "howell township",
        "marlboro": "marlboro township",
        "marlboro twp": "marlboro township",
        "marlboro township": "marlboro township",
    }
    return aliases.get(text, text)


def _parcel_value(parcel: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(parcel.get(key))
        if value:
            return value
    return ""


def adapt_parcel_zoning_evidence(
    *,
    municipality: str | None,
    parcel: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate a normalized parcel-specific zoning evidence record.

    The adapter resolves only when the evidence itself supplies:
      * the municipality;
      * Block and Lot matching the requested parcel;
      * a non-empty zoning district;
      * an authoritative source explicitly marked as such.

    Missing or conflicting evidence returns VERIFY.  No zoning district is
    inferred from municipality, source role, or a generic zoning map alone.
    """
    parcel_data = parcel or {}
    record = evidence or {}
    source = record.get("source") or {}

    block = _parcel_value(parcel_data, "block", "Block")
    lot = _parcel_value(parcel_data, "lot", "Lot")
    evidence_block = _parcel_value(record, "block", "Block")
    evidence_lot = _parcel_value(record, "lot", "Lot")
    evidence_municipality = record.get("municipality") or source.get("municipality")
    district = _text(
        record.get("zoning_district")
        or record.get("district")
        or record.get("zoning")
    )

    valid = all((
        _norm(municipality),
        _norm(evidence_municipality),
        _norm(municipality) == _norm(evidence_municipality),
        block,
        lot,
        _norm(block) == _norm(evidence_block),
        _norm(lot) == _norm(evidence_lot),
        district,
        source.get("authoritative") is True,
    ))

    if not valid:
        return {
            "status": "ZONING_NOT_RESOLVED",
            "zoning_district": "VERIFY",
            "authoritative": False,
            "evidence_type": "NONE",
            "reason": (
                "Structured evidence did not provide a verified, "
                "authoritative municipality + Block + Lot zoning match."
            ),
        }

    return {
        "municipality": municipality,
        "block": block,
        "lot": lot,
        "status": "ZONING_RESOLVED",
        "zoning_district": district,
        "authoritative": True,
        "evidence_type": record.get(
            "evidence_type", "PARCEL_SPECIFIC_SOURCE"
        ),
        "source": {
            "source_type": source.get("source_type", "municipal_zoning_source"),
            "url": source.get("url"),
            "description": source.get("description"),
            "authoritative": True,
        },
        "parcel_reference": {
            "block": evidence_block,
            "lot": evidence_lot,
        },
        "reason": (
            "Authoritative structured zoning evidence matched the requested "
            "municipality and Block/Lot."
        ),
    }
