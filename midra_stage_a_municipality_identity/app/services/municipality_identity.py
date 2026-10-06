from __future__ import annotations

from typing import Any

from app.services.zoning_intelligence import MUNICIPALITY_SOURCES

# Stage A identity mapping only. This does not imply zoning coverage.
KNOWN_NJ_MUNICIPALITY_CODES: dict[str, str] = {
    "howell township": "1321",
    "marlboro township": "1322",
}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _canonical_from_registry(municipality: str | None) -> str | None:
    key = _normalize(municipality)
    if not key:
        return None

    aliases = {
        "howell": "howell township",
        "howell twp": "howell township",
        "marlboro": "marlboro township",
        "marlboro twp": "marlboro township",
    }
    registry_key = aliases.get(key, key)

    config = MUNICIPALITY_SOURCES.get(registry_key)
    if config:
        return str(config.get("canonical_name") or registry_key)

    for config in MUNICIPALITY_SOURCES.values():
        if _normalize(config.get("canonical_name")) == key:
            return str(config.get("canonical_name") or key)

    return None


def resolve_municipality_identity(
    municipality: str | None,
    *,
    county: str | None = None,
    state: str | None = "New Jersey",
    municipality_code: str | None = None,
) -> dict[str, Any]:
    """Resolve municipality identity without making zoning claims."""
    supplied = str(municipality or "").strip()
    canonical = _canonical_from_registry(supplied)

    if not canonical:
        return {
            "status": "MUNICIPALITY_NOT_RECOGNIZED",
            "recognized": False,
            "municipality": supplied or None,
            "canonical_name": None,
            "county": county,
            "state": state,
            "municipality_code": municipality_code,
            "identity_source": {
                "source_type": "NJ Office of GIS",
                "authoritative": True,
                "mode": "stage_a_registry_identity",
            },
            "notes": [
                "Municipality identity could not be matched to the "
                "currently loaded MIDRA identity registry.",
                "This does not establish that the municipality lacks "
                "authoritative zoning information.",
            ],
        }

    normalized = _normalize(canonical)
    config = MUNICIPALITY_SOURCES.get(normalized) or {}

    return {
        "status": "MUNICIPALITY_RECOGNIZED",
        "recognized": True,
        "municipality": supplied or canonical,
        "canonical_name": canonical,
        "county": county or config.get("county"),
        "state": state or config.get("state") or "New Jersey",
        "municipality_code": (
            municipality_code
            or KNOWN_NJ_MUNICIPALITY_CODES.get(normalized)
        ),
        "identity_source": {
            "source_type": "NJ Office of GIS",
            "authoritative": True,
            "mode": "stage_a_registry_identity",
        },
        "notes": [
            "Stage A establishes municipality identity only.",
            "Municipality recognition does not imply zoning-source "
            "verification or project-rule availability.",
        ],
    }


build_municipality_identity = resolve_municipality_identity
