from __future__ import annotations

import json
from typing import Any

import httpx


def query_arcgis_zoning_by_geometry(
    *,
    service_url: str,
    district_field: str,
    geometry: dict[str, Any],
    municipality: str | None = None,
    spatial_reference_wkid: int | str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Query an explicitly discovered ArcGIS zoning polygon layer by parcel geometry.

    This provider is deliberately non-authoritative. It only reports candidate
    zoning evidence returned by the explicitly supplied service URL/field.
    """
    if not service_url or not service_url.lower().startswith(("https://", "http://")):
        return {"status": "ZONING_NOT_RESOLVED", "reason": "INVALID_SERVICE_URL"}

    if not district_field or not isinstance(geometry, dict) or not geometry:
        return {"status": "ZONING_NOT_RESOLVED", "reason": "INVALID_QUERY_INPUT"}

    query_url = service_url.rstrip("/") + "/query"
    spatial_reference = geometry.get("spatialReference") or {}
    in_sr = (
        spatial_reference.get("wkid")
        or spatial_reference.get("latestWkid")
        or spatial_reference_wkid
    )
    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryPolygon",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": district_field,
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "6",
        "f": "json",
    }
    if in_sr is not None:
        params["inSR"] = str(in_sr)

    try:
        response = httpx.post(query_url, data=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "status": "ZONING_NOT_RESOLVED",
            "reason": "ARCGIS_QUERY_FAILED",
            "error": str(exc),
        }

    if payload.get("error"):
        return {
            "status": "ZONING_NOT_RESOLVED",
            "reason": "ARCGIS_QUERY_ERROR",
            "error": payload["error"],
        }

    features = payload.get("features") or []
    candidates: list[dict[str, Any]] = []
    for feature in features:
        attrs = feature.get("attributes") or {}
        district = attrs.get(district_field)
        if district is None:
            continue
        district = str(district).strip()
        if not district:
            continue
        mapped_geometry = feature.get("geometry")
        candidates.append({
            "district": district,
            "attributes": attrs,
            "mapped_geometry": mapped_geometry if isinstance(mapped_geometry, dict) else None,
        })

    unique = {}
    for candidate in candidates:
        unique.setdefault(candidate["district"].casefold(), candidate)

    if len(unique) != 1:
        return {
            "status": "ZONING_NOT_RESOLVED",
            "reason": "NO_UNIQUE_DISTRICT" if not unique else "AMBIGUOUS_DISTRICT",
            "candidates": list(unique.values()),
            "source": {
                "url": service_url,
                "district_field": district_field,
                "municipality": municipality,
                "authoritative": False,
            },
        }

    candidate = next(iter(unique.values()))
    resolved_key = candidate["district"].casefold()
    mapped_geometries = [
        item["mapped_geometry"]
        for item in candidates
        if item["district"].casefold() == resolved_key
        and isinstance(item.get("mapped_geometry"), dict)
    ]
    return {
        "status": "ZONING_CANDIDATE_RESOLVED",
        "district": candidate["district"],
        "attributes": candidate["attributes"],
        "mapped_geometries": mapped_geometries,
        "geometry_role": "ZONING_CANDIDATE_GIS_GEOMETRY" if mapped_geometries else None,
        "geometry_definitive": False,
        "source": {
            "url": service_url,
            "district_field": district_field,
            "municipality": municipality,
            "authoritative": False,
        },
    }
