from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip()


def _normalize(value: object) -> str:
    return " ".join(_text(value).lower().split())


def _parcel_value(parcel: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(parcel.get(key))
        if value:
            return value
    return ""


# Stage C contains only verified parcel-specific zoning evidence.
# Municipality registration alone never establishes zoning.
PARCEL_ZONING_EVIDENCE: dict[str, list[dict[str, Any]]] = {
    "howell township": [
        {
            "block": "177",
            "lot": "16.01",
            "zoning_district": "HD-4",
            "evidence_type": "OFFICIAL_PARCEL_SPECIFIC",
            "source_type": "municipal_zoning_evidence",
            "authoritative": True,
            "source_description": (
                "Howell Township official parcel-specific zoning evidence "
                "used by MIDRA for the verified HD-4 test property."
            ),
        },
    ],
    "marlboro township": [
        {
            "block": "177",
            "lot": "16",
            "zoning_district": "CF",
            "evidence_type": "OFFICIAL_PARCEL_SPECIFIC",
            "source_type": "municipal_zoning_evidence",
            "authoritative": True,
            "source_description": (
                "Marlboro Township official parcel-specific zoning evidence "
                "used by MIDRA for the verified CF test property."
            ),
        },
    ],
}


def resolve_zoning_evidence(
    *,
    municipality: str | None,
    parcel: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return Stage C property-specific zoning evidence safely."""

    parcel_data = parcel or {}
    municipality_key = _normalize(municipality)
    block = _parcel_value(parcel_data, "block", "Block")
    lot = _parcel_value(parcel_data, "lot", "Lot")

    base = {
        "municipality": municipality,
        "block": block or None,
        "lot": lot or None,
    }

    if not municipality_key:
        return {
            **base,
            "status": "ZONING_NOT_RESOLVED",
            "zoning_district": "VERIFY",
            "evidence_type": "NONE",
            "authoritative": False,
            "source": None,
            "reason": (
                "Municipality is unavailable, so property-specific zoning "
                "evidence cannot be evaluated."
            ),
        }

    if not block or not lot:
        return {
            **base,
            "status": "ZONING_NOT_RESOLVED",
            "zoning_district": "VERIFY",
            "evidence_type": "NONE",
            "authoritative": False,
            "source": None,
            "reason": (
                "Authoritative parcel-specific zoning requires usable "
                "Block and Lot evidence."
            ),
        }

    for item in PARCEL_ZONING_EVIDENCE.get(municipality_key, []):
        if (
            _normalize(item["block"]) == _normalize(block)
            and _normalize(item["lot"]) == _normalize(lot)
        ):
            return {
                **base,
                "status": "ZONING_RESOLVED",
                "zoning_district": item["zoning_district"],
                "evidence_type": item["evidence_type"],
                "authoritative": bool(item["authoritative"]),
                "source": {
                    "source_type": item["source_type"],
                    "description": item["source_description"],
                    "authoritative": bool(item["authoritative"]),
                },
                "reason": (
                    "The zoning district is supported by verified "
                    "municipality + Block + Lot evidence."
                ),
            }

    return {
        **base,
        "status": "ZONING_NOT_RESOLVED",
        "zoning_district": "VERIFY",
        "evidence_type": "NONE",
        "authoritative": False,
        "source": None,
        "reason": (
            "No verified parcel-specific zoning evidence is currently "
            "registered for this municipality and Block/Lot combination."
        ),
    }
