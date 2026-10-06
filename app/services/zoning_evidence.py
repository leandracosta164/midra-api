from __future__ import annotations

from app.services.zoning_evidence_adapter import adapt_parcel_zoning_evidence
from app.services.zoning_evidence_registry import get_verified_zoning_evidence

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip()


def _normalize(value: object) -> str:
    text = " ".join(_text(value).lower().split())
    aliases = {
        "marlboro township": "marlboro twp",
        "howell township": "howell twp",
    }
    return aliases.get(text, text)


def _parcel_value(parcel: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(parcel.get(key))
        if value:
            return value
    return ""


def _same_parcel(
    parcel: dict[str, Any],
    zoning_resolution: dict[str, Any],
) -> bool:
    reference = zoning_resolution.get("parcel_reference") or {}

    parcel_block = _parcel_value(parcel, "block", "Block")
    parcel_lot = _parcel_value(parcel, "lot", "Lot")

    resolved_block = _parcel_value(reference, "block", "Block")
    resolved_lot = _parcel_value(reference, "lot", "Lot")

    return (
        bool(parcel_block)
        and bool(parcel_lot)
        and _normalize(parcel_block) == _normalize(resolved_block)
        and _normalize(parcel_lot) == _normalize(resolved_lot)
    )


def resolve_zoning_evidence(
    *,
    municipality: str | None,
    parcel: dict[str, Any] | None,
    zoning_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Stage C evidence bridge.

    A verified parcel-specific zoning result from the existing zoning
    resolver is treated as Stage C evidence only when:
      - status is ZONING_RESOLVED;
      - confidence is OFFICIAL_PARCEL_SPECIFIC;
      - source is authoritative;
      - the zoning parcel reference matches the current Block/Lot.

    The legacy standalone Stage C test registry remains available for the
    two original verified test parcels.
    """

    parcel_data = parcel or {}
    resolution = zoning_resolution or {}

    municipality_value = municipality
    block = _parcel_value(parcel_data, "block", "Block")
    lot = _parcel_value(parcel_data, "lot", "Lot")

    resolution_source = resolution.get("source") or {}
    resolution_municipality = (
        resolution.get("municipality")
        or resolution_source.get("municipality")
    )

    adapted_resolution = adapt_parcel_zoning_evidence(
        municipality=municipality_value,
        parcel=parcel_data,
        evidence={
            "municipality": resolution_municipality,
            "block": _parcel_value(
                resolution.get("parcel_reference") or {},
                "block",
                "Block",
            ),
            "lot": _parcel_value(
                resolution.get("parcel_reference") or {},
                "lot",
                "Lot",
            ),
            "zoning_district": resolution.get("zoning_district"),
            "evidence_type": resolution.get(
                "confidence", "PARCEL_SPECIFIC_SOURCE"
            ),
            "source": resolution_source,
        },
    )

    if (
        adapted_resolution.get("status") == "ZONING_RESOLVED"
        and resolution.get("confidence") == "OFFICIAL_PARCEL_SPECIFIC"
        and _same_parcel(parcel_data, resolution)
    ):
        source = resolution.get("source") or {}
        zoning_name = _text(resolution.get("zoning_name"))

        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": _text(
                resolution.get("zoning_district")
            ) or "VERIFY",
            "evidence_type": "OFFICIAL_PARCEL_SPECIFIC",
            "authoritative": True,
            "source": {
                "source_type": source.get(
                    "source_type",
                    "existing_zoning_resolution",
                ),
                "url": source.get("url"),
                "description": source.get("description"),
                "authoritative": True,
                "zoning_name": zoning_name or None,
            },
            "parcel_reference": {
                "block": _parcel_value(
                    resolution.get("parcel_reference") or {},
                    "block",
                    "Block",
                ),
                "lot": _parcel_value(
                    resolution.get("parcel_reference") or {},
                    "lot",
                    "Lot",
                ),
            },
            "reason": (
                "Stage C inherited authoritative parcel-specific zoning "
                "evidence from the existing zoning resolver after verifying "
                "the Block/Lot match."
            ),
        }

    if zoning_resolution is not None:
        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_NOT_RESOLVED",
            "zoning_district": "VERIFY",
            "evidence_type": "NONE",
            "authoritative": False,
            "source": None,
            "reason": (
                "Supplied zoning resolution did not pass the generic "
                "parcel-specific evidence validation, so MIDRA will not "
                "fall back to a conflicting or unrelated zoning record."
            ),
        }

    municipality_key = _normalize(municipality_value)
    registry_record = get_verified_zoning_evidence(
        municipality_key=municipality_key,
        block=_normalize(block),
        lot=_normalize(lot),
    )

    if registry_record:
        district = _text(registry_record.get("zoning_district"))
        registry_source = registry_record.get("source") or {}

        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": district or "VERIFY",
            "evidence_type": "OFFICIAL_PARCEL_SPECIFIC",
            "authoritative": True,
            "source": {
                "source_type": registry_source.get(
                    "source_type",
                    "municipal_zoning_evidence",
                ),
                "description": registry_source.get(
                    "description",
                    "Verified Stage D parcel-specific zoning evidence "
                    "registered for this property.",
                ),
                "authoritative": bool(
                    registry_source.get("authoritative", True)
                ),
            },
            "reason": (
                "The zoning district is supported by verified "
                "municipality + Block + Lot evidence."
            ),
        }

    return {
        "municipality": municipality_value,
        "block": block or None,
        "lot": lot or None,
        "status": "ZONING_NOT_RESOLVED",
        "zoning_district": "VERIFY",
        "evidence_type": "NONE",
        "authoritative": False,
        "source": None,
        "reason": (
            "No verified parcel-specific zoning evidence is currently "
            "available for this municipality and Block/Lot combination."
        ),
    }
