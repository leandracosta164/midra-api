from __future__ import annotations

from typing import Any

from app.services.zoning_intelligence import (
    MUNICIPALITY_SOURCES,
)


def _normalize(value: object) -> str:
    return " ".join(
        str(value or "").strip().lower().split()
    )


def _is_registered(municipality: str | None) -> bool:
    key = _normalize(municipality)

    if not key:
        return False

    if key in MUNICIPALITY_SOURCES:
        return True

    # Match canonical names as a fallback.
    for config in MUNICIPALITY_SOURCES.values():
        if _normalize(
            config.get("canonical_name")
        ) == key:
            return True

    # Common NJ parcel-service abbreviation handling.
    aliases = {
        "howell": "howell township",
        "howell twp": "howell township",
        "marlboro": "marlboro township",
        "marlboro twp": "marlboro township",
    }

    return aliases.get(
        key,
        key,
    ) in MUNICIPALITY_SOURCES


def build_municipality_coverage(
    *,
    municipality: str | None,
    zoning_intelligence: dict[str, Any] | None,
    zoning_resolution: dict[str, Any] | None = None,
    project_goal: str | None = None,
    municipality_source_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return explicit MIDRA coverage metadata.

    This is intentionally derived from the same registry and
    rules result used by the zoning engine. It does not infer
    support merely because a municipality is registered.

    Coverage levels:

    - municipality_registered:
        The municipality exists in MIDRA's authoritative source
        registry.

    - zoning_resolution_supported:
        The parcel-specific zoning resolver returned a verified
        zoning district.

    - district_rules_supported:
        A verified district has authoritative district/bulk rules
        available in the zoning intelligence result.

    - project_rules_supported:
        Project-specific requirements are actually available for
        the requested municipality/district/project result.
    """
    zoning = zoning_intelligence or {}
    resolution = zoning_resolution or {}

    registered = _is_registered(municipality)
    source_registry = municipality_source_registry or {}
    source_identified = bool(source_registry.get("registered") is True)
    source_registry_status = str(source_registry.get("status") or "").strip() or None

    resolved_district = str(
        resolution.get("zoning_district")
        or zoning.get("zoning_district")
        or ""
    ).strip()

    zoning_confidence = str(
        resolution.get("confidence")
        or ""
    ).strip()

    zoning_resolved = (
        resolved_district
        and resolved_district.upper() != "VERIFY"
        and zoning_confidence == "OFFICIAL_PARCEL_SPECIFIC"
    )

    bulk_requirements = zoning.get(
        "bulk_requirements"
    ) or []

    project_requirements = zoning.get(
        "project_requirements"
    ) or []

    district_rules_supported = bool(
        zoning_resolved
        and bulk_requirements
    )

    project_rules_supported = bool(
        zoning_resolved
        and project_requirements
    )

    # A registered municipality with no verified parcel zoning
    # must never be represented as having district support for
    # the property.
    if not registered:
        zoning_resolved = False
        district_rules_supported = False
        project_rules_supported = False

    status = "SOURCE_IDENTIFIED_VERIFY" if source_identified else "UNREGISTERED"

    if registered:
        status = "REGISTERED"

        if zoning_resolved:
            status = "ZONING_RESOLVED"

            if district_rules_supported:
                status = "DISTRICT_RULES_AVAILABLE"

            if project_rules_supported:
                status = "PROJECT_RULES_AVAILABLE"

    return {
        "status": status,
        "municipality_registered": bool(
            registered
        ),
        "municipality_source_identified": bool(source_identified or registered),
        "municipality_source_status": source_registry_status,
        "zoning_resolution_supported": bool(
            zoning_resolved
        ),
        "district_rules_supported": bool(
            district_rules_supported
        ),
        "project_rules_supported": bool(
            project_rules_supported
        ),
        "municipality": (
            municipality
            or zoning.get("municipality")
        ),
        "zoning_district": (
            resolved_district
            or "VERIFY"
        ),
        "project_goal": project_goal,
    }

