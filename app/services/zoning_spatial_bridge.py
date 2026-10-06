"""Non-breaking bridge from selected zoning sources to spatial zoning candidates.

This module orchestrates only the dynamic candidate path. It does not replace
legacy zoning evidence, mark a source authoritative, or mutate the database.
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse

from app.services.arcgis_application_metadata import retrieve_arcgis_application_metadata
from app.services.arcgis_service_discovery import extract_arcgis_item_id
from app.services.arcgis_spatial_zoning_provider import query_arcgis_zoning_by_geometry
from app.services.arcgis_webmap_service_discovery import discover_arcgis_webmap_services
from app.services.zoning_source_selector import select_zoning_source_candidates
from app.services.source_authority import evaluate_source_authority


def _is_feature_service(url: str) -> bool:
    return "/featureserver/" in (urlparse(url).path or "").lower()


def _candidate_from_query(
    *,
    municipality: str,
    block: str,
    lot: str,
    source: dict[str, Any],
    query_result: dict[str, Any],
) -> dict[str, Any] | None:
    if query_result.get("status") != "ZONING_CANDIDATE_RESOLVED":
        return None
    district = str(query_result.get("district") or "").strip()
    if not district:
        return None
    query_source = dict(query_result.get("source") or {})
    merged_source = dict(source)
    merged_source.update(query_source)

    # Spatial resolution must not invent authority, but it must also not erase
    # authority/legal-control decisions that were explicitly persisted in the
    # source catalog. Provider metadata is candidate evidence only and cannot
    # promote (or demote) the catalog's trust state.
    merged_source["authoritative"] = source.get("authoritative") is True
    merged_source["legal_control_confirmed"] = source.get("legal_control_confirmed") is True
    merged_source["authority_evaluation"] = evaluate_source_authority(
        source=merged_source,
        municipality=municipality,
    )
    return {
        "status": "ZONING_CANDIDATE_RESOLVED",
        "record": {
            "municipality": municipality,
            "block": str(block),
            "lot": str(lot),
            "zoning_district": district,
            "source": merged_source,
            "evidence_type": "ARCGIS_SPATIAL_INTERSECTION",
            "attributes": query_result.get("attributes") or {},
            "mapped_geometries": query_result.get("mapped_geometries") or [],
            "geometry_role": query_result.get("geometry_role"),
            "geometry_definitive": False,
        },
    }


def resolve_dynamic_spatial_zoning_candidate(
    *,
    municipality: str,
    block: str,
    lot: str,
    geometry: dict[str, Any],
    db: Any,
    metadata_retriever: Callable[..., dict[str, Any]] = retrieve_arcgis_application_metadata,
    webmap_discoverer: Callable[[dict[str, Any]], dict[str, Any]] = discover_arcgis_webmap_services,
    spatial_query: Callable[..., dict[str, Any]] = query_arcgis_zoning_by_geometry,
) -> dict[str, Any]:
    """Return the first unique dynamic ArcGIS zoning candidate, if available.

    The function is intentionally parallel to the legacy zoning path. A
    candidate is never promoted to authoritative zoning here.
    """
    candidates = select_zoning_source_candidates(municipality=municipality, db=db)
    zoning_maps = [item for item in candidates if item.get("source_role") == "zoning_map"]

    if not zoning_maps:
        return {
            "status": "ZONING_NOT_RESOLVED",
            "reason": "NO_DYNAMIC_ZONING_MAP_SOURCE",
            "candidates": [],
        }

    attempted: list[dict[str, Any]] = []
    for source in zoning_maps:
        source_url = str(source.get("source_url") or "").strip()
        if not source_url:
            continue

        services: list[dict[str, Any]] = []
        if _is_feature_service(source_url):
            district_field = str(source.get("district_field") or "").strip()
            if district_field:
                services.append({"url": source_url, "district_field": district_field, "title": source.get("label")})
        else:
            item_id = extract_arcgis_item_id(source_url)
            if not item_id:
                attempted.append({"source_url": source_url, "reason": "NO_EXPLICIT_ARCGIS_ITEM_ID"})
                continue
            app_result = metadata_retriever(item_id)
            if app_result.get("status") != "ARCGIS_METADATA_RETRIEVED":
                attempted.append({"source_url": source_url, "reason": app_result.get("status", "ARCGIS_METADATA_FAILED")})
                continue
            data = app_result.get("data") or {}
            webmap_id = str((data.get("values") or {}).get("webmap") or "").strip()
            if len(webmap_id) != 32:
                attempted.append({"source_url": source_url, "reason": "WEBMAP_ID_NOT_FOUND"})
                continue
            webmap_result = metadata_retriever(webmap_id)
            if webmap_result.get("status") != "ARCGIS_METADATA_RETRIEVED":
                attempted.append({"source_url": source_url, "reason": webmap_result.get("status", "WEBMAP_METADATA_FAILED")})
                continue
            service_result = webmap_discoverer(webmap_result.get("data") or {})
            services.extend(
                layer for layer in service_result.get("layers") or []
                if layer.get("district_field")
            )

        for service in services:
            result = spatial_query(
                service_url=str(service.get("url") or ""),
                district_field=str(service.get("district_field") or ""),
                geometry=geometry,
                municipality=municipality,
                spatial_reference_wkid=4326,
            )
            candidate = _candidate_from_query(
                municipality=municipality,
                block=block,
                lot=lot,
                source={
                    **source,
                    "discovered_service_url": service.get("url"),
                    "discovered_service_title": service.get("title"),
                    "discovered_district_field": service.get("district_field"),
                },
                query_result=result,
            )
            if candidate is not None:
                return candidate
            attempted.append({
                "source_url": source_url,
                "service_url": service.get("url"),
                "reason": result.get("reason", result.get("status", "NO_CANDIDATE")),
            })

    return {
        "status": "ZONING_NOT_RESOLVED",
        "reason": "NO_UNIQUE_DYNAMIC_ZONING_CANDIDATE",
        "attempted": attempted,
    }
