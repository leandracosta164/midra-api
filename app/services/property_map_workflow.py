"""Bridge property-map intelligence into the normal property workflow."""
from __future__ import annotations

from typing import Any

from app.services.property_map_intelligence import resolve_property_maps


def _flatten_registry_sources(registry: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Convert Stage-B registry sources into map-intelligence source records."""
    registry = registry or {}
    flattened: list[dict[str, Any]] = []
    sources = registry.get("sources") or {}

    for key, value in sources.items():
        if not isinstance(value, dict):
            continue
        url = str(value.get("url") or "").strip()
        if not url:
            continue

        key_text = str(key or "").strip().lower()
        source_type = str(value.get("source_type") or "").strip().lower()

        if "tax" in key_text and "map" in key_text:
            role = "tax_map"
        elif "tax_map" in source_type or "tax map" in source_type:
            role = "tax_map"
        elif "zoning" in key_text and "map" in key_text:
            role = "zoning_map"
        elif "zoning_map" in source_type or "zoning map" in source_type:
            role = "zoning_map"
        else:
            role = value.get("source_role")

        flattened.append({
            "label": str(value.get("label") or key).replace("_", " ").strip(),
            "source_url": url,
            "source_role": role,
            "authoritative": value.get("authoritative") is True,
            "municipal_official_link_verified": value.get("municipal_official_link_verified") is True,
            "authority_verified": value.get("authority_verified") is True,
            "tax_map_sheet": value.get("tax_map_sheet") or value.get("sheet"),
            "block": value.get("block"),
            "lot": value.get("lot"),
            "source_type": value.get("source_type"),
            "discovered_from": value.get("discovered_from"),
        })

    return flattened


def resolve_property_map_workflow(
    *,
    municipality: str | None,
    block: str | None,
    lot: str | None,
    municipality_source_registry: dict[str, Any] | None,
    zoning_resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve map artifacts for the already-resolved property.

    This is read-only and does not alter zoning, legal control, or approval logic.
    """
    if not municipality:
        return {
            "status": "VERIFY",
            "reason": "MUNICIPALITY_NOT_RESOLVED",
            "zoning_map": {"status": "VERIFY", "reason": "MUNICIPALITY_NOT_RESOLVED"},
            "tax_map": {"status": "VERIFY", "reason": "MUNICIPALITY_NOT_RESOLVED"},
        }

    sources = _flatten_registry_sources(municipality_source_registry)
    return resolve_property_maps(
        municipality=municipality,
        block=str(block or ""),
        lot=str(lot or ""),
        sources=sources,
        zoning_result=zoning_resolution,
    )
