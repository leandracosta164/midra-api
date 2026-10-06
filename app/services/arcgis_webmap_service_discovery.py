"""Discover explicit ArcGIS feature services from retrieved Web Map data.

This module only follows references explicitly present in ArcGIS Web Map data.
It never constructs or guesses a service URL from an item ID.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


_DISTRICT_FIELD_NAMES = {
    "zoning_district",
    "zoningdistrict",
    "zoning_zone",
    "zoningzone",
    "zone",
    "district",
    "zone_code",
    "zonecode",
}


def _looks_like_feature_service(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return parsed.scheme in {"http", "https"} and "/featureserver/" in path


def _district_field(layer: dict[str, Any]) -> str | None:
    candidates: list[str] = []
    for collection_key in ("fields", "fieldConfigurations"):
        values = layer.get(collection_key)
        if not isinstance(values, list):
            continue
        for entry in values:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            alias = entry.get("alias")
            for value in (name, alias):
                if value is not None and str(value).strip():
                    candidates.append(str(value).strip())
    for candidate in candidates:
        normalized = candidate.lower().replace(" ", "_")
        if normalized in _DISTRICT_FIELD_NAMES:
            return candidate
    return None


def discover_arcgis_webmap_services(data: dict[str, Any]) -> dict[str, Any]:
    """Return explicit operational feature-service references from Web Map data."""
    if not isinstance(data, dict):
        return {"status": "WEBMAP_DATA_INVALID", "layers": []}

    operational_layers = data.get("operationalLayers")
    if not isinstance(operational_layers, list):
        return {"status": "WEBMAP_OPERATIONAL_LAYERS_NOT_FOUND", "layers": []}

    discovered: list[dict[str, Any]] = []
    for layer in operational_layers:
        if not isinstance(layer, dict):
            continue
        url = str(layer.get("url") or "").strip()
        if not _looks_like_feature_service(url):
            continue
        discovered.append(
            {
                "url": url,
                "title": str(layer.get("title") or "").strip(),
                "item_id": str(layer.get("itemId") or "").strip() or None,
                "layer_type": str(layer.get("layerType") or "").strip() or None,
                "district_field": _district_field(layer.get("layerDefinition") or {})
                if isinstance(layer.get("layerDefinition"), dict)
                else _district_field(layer),
            }
        )

    return {
        "status": "WEBMAP_SERVICES_DISCOVERED" if discovered else "WEBMAP_FEATURE_SERVICES_NOT_FOUND",
        "layers": discovered,
    }
