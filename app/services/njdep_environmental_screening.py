"""Authoritative-source environmental GIS screening providers for MIDRA Property.

This module establishes a conservative NJDEP wetlands screening contract. A mapped
intersection is evidence for screening, not a regulatory boundary determination.
A zero-feature response is likewise not proof that regulated wetlands are absent.
"""
from __future__ import annotations

from typing import Any, Callable
from datetime import datetime, timezone
import json
import httpx

NJDEP_WETLANDS_2012_LAYER = "https://mapsdep.nj.gov/arcgis/rest/services/Features/Land_lu/MapServer/2"
NJDEP_WETLANDS_SOURCE_PAGE = "https://mapsdep.nj.gov/arcgis/rest/services/Features/Land_lu/MapServer/2"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _wetlands_source(*, observed_at: str | None = None, retrieved: bool = False, source_url: str = NJDEP_WETLANDS_SOURCE_PAGE) -> dict[str, Any]:
    return {
        "agency": "New Jersey Department of Environmental Protection",
        "dataset": "Wetlands (2012)",
        "url": source_url,
        "authoritative_agency_source": True,
        "current_status": "VERIFY_CURRENTNESS",
        "last_checked_at": observed_at,
        "retrieved_at": observed_at if retrieved else None,
        "currentness_note": (
            "The authoritative NJDEP layer was queried at the recorded check time, but the dataset title identifies a 2012 vintage. "
            "MIDRA does not infer that mapped content is legally or professionally current; current applicability requires verification."
        ),
    }

def _flood_source(*, observed_at: str | None = None, retrieved: bool = False) -> dict[str, Any]:
    return {
        "agency": "FEMA / New Jersey Department of Environmental Protection",
        "dataset": "National Flood Hazard Layer (NFHL)",
        "url": NJDEP_FEMA_NFHL_LAYER,
        "authoritative_agency_source": True,
        "current_status": "VERIFY_CURRENTNESS",
        "last_checked_at": observed_at,
        "retrieved_at": observed_at if retrieved else None,
        "currentness_note": (
            "MIDRA queried the authoritative NJDEP-hosted FEMA NFHL layer at the recorded check time, but did not independently establish an effective-date/currentness guarantee for the returned mapping. "
            "Current FEMA/NJDEP applicability requires verification before professional reliance."
        ),
    }

def _verify(reason: str, *, source_url: str = NJDEP_WETLANDS_2012_LAYER, observed_at: str | None = None, retrieved: bool = False) -> dict[str, Any]:
    return {
        "status": "VERIFY",
        "screening_result": "NOT_ESTABLISHED",
        "mapped_intersection": None,
        "regulatory_determination": False,
        "source": _wetlands_source(observed_at=observed_at, retrieved=retrieved, source_url=source_url),
        "reason": reason,
    }

def screen_njdep_wetlands_point(
    *,
    longitude: float | int | None,
    latitude: float | int | None,
    timeout: float = 20.0,
    post: Callable[..., Any] = httpx.post,
) -> dict[str, Any]:
    """Screen a resolved property coordinate against the NJDEP Wetlands (2012) layer.

    This is intentionally a screening result only. NJDEP itself cautions that its
    public GIS mapping is guidance and does not establish exact regulated boundaries.
    """
    try:
        x=float(longitude)  # longitude
        y=float(latitude)   # latitude
    except (TypeError, ValueError):
        return _verify("PROPERTY_COORDINATES_NOT_RESOLVED")

    if not (-180 <= x <= 180 and -90 <= y <= 90):
        return _verify("INVALID_PROPERTY_COORDINATES")

    params={
        "geometry": f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "OBJECTID,LABEL12,TYPE12,ACRES",
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "6",
        "f": "json",
    }
    observed_at = _utc_now_iso()
    try:
        response=post(NJDEP_WETLANDS_2012_LAYER.rstrip("/")+"/query", data=params, timeout=timeout)
        response.raise_for_status()
        payload=response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        result=_verify("NJDEP_WETLANDS_QUERY_FAILED", observed_at=observed_at)
        result["error"]=str(exc)
        return result

    if payload.get("error"):
        result=_verify("NJDEP_WETLANDS_QUERY_ERROR", observed_at=observed_at, retrieved=True)
        result["error"]=payload["error"]
        return result

    features=payload.get("features")
    if not isinstance(features,list):
        return _verify("NJDEP_WETLANDS_RESPONSE_INVALID", observed_at=observed_at, retrieved=True)

    evidence=[]
    for feature in features:
        attrs=(feature or {}).get("attributes") or {}
        geometry=(feature or {}).get("geometry")
        evidence.append({
            "label": attrs.get("LABEL12"),
            "type": attrs.get("TYPE12"),
            "acres": attrs.get("ACRES"),
            "object_id": attrs.get("OBJECTID"),
            "mapped_geometry": geometry if isinstance(geometry, dict) else None,
            "geometry_role": "AUTHORITATIVE_GIS_SCREENING_GEOMETRY" if isinstance(geometry, dict) else None,
            "geometry_definitive": False,
        })

    intersects=bool(evidence)
    return {
        "status": "SCREENING_COMPLETE",
        "screening_result": "MAPPED_WETLANDS_INTERSECTION" if intersects else "NO_MAPPED_INTERSECTION_RETURNED",
        "mapped_intersection": intersects,
        "regulatory_determination": False,
        "evidence": evidence,
        "source": _wetlands_source(observed_at=observed_at, retrieved=True),
        "limitations": [
            "Returned GIS polygon geometry is mapped screening evidence, not a surveyed, definitive, or regulatory wetlands boundary.",
            "No mapped intersection returned does not establish that regulated wetlands are absent.",
            "Dataset vintage and current regulatory applicability must be verified before professional reliance.",
        ],
    }


NJDEP_FEMA_NFHL_LAYER = "https://mapsdep.nj.gov/arcgis/rest/services/Features/Hydrography/MapServer/43"

def screen_njdep_fema_flood_point(*, longitude: float | int | None, latitude: float | int | None, timeout: float = 20.0, post: Callable[..., Any] = httpx.post) -> dict[str, Any]:
    """Screen a coordinate against FEMA NFHL polygons published by NJDEP."""
    source=_flood_source()
    try: x=float(longitude); y=float(latitude)
    except (TypeError,ValueError):
        return {"status":"VERIFY","screening_result":"NOT_ESTABLISHED","mapped_intersection":None,"regulatory_determination":False,"actual_flood_risk_calculated":False,"reason":"PROPERTY_COORDINATES_NOT_RESOLVED","source":source}
    if not (-180<=x<=180 and -90<=y<=90):
        return {"status":"VERIFY","screening_result":"NOT_ESTABLISHED","mapped_intersection":None,"regulatory_determination":False,"actual_flood_risk_calculated":False,"reason":"INVALID_PROPERTY_COORDINATES","source":source}
    params={"geometry":f"{x},{y}","geometryType":"esriGeometryPoint","inSR":"4326","spatialRel":"esriSpatialRelIntersects","outFields":"OBJECTID,FLD_ZONE,ZONE_SUBTY","returnGeometry":"true","outSR":"4326","geometryPrecision":"6","f":"json"}
    observed_at=_utc_now_iso()
    try:
        response=post(NJDEP_FEMA_NFHL_LAYER+"/query",data=params,timeout=timeout); response.raise_for_status(); payload=response.json()
    except (httpx.HTTPError,ValueError,TypeError) as exc:
        return {"status":"VERIFY","screening_result":"NOT_ESTABLISHED","mapped_intersection":None,"regulatory_determination":False,"actual_flood_risk_calculated":False,"reason":"NFHL_QUERY_FAILED","error":str(exc),"source":_flood_source(observed_at=observed_at)}
    if payload.get("error") or not isinstance(payload.get("features"),list):
        return {"status":"VERIFY","screening_result":"NOT_ESTABLISHED","mapped_intersection":None,"regulatory_determination":False,"actual_flood_risk_calculated":False,"reason":"NFHL_RESPONSE_INVALID","error":payload.get("error"),"source":_flood_source(observed_at=observed_at,retrieved=True)}
    evidence=[]
    for feature in payload["features"]:
        attrs=(feature or {}).get("attributes") or {}
        geometry=(feature or {}).get("geometry")
        evidence.append({"flood_zone":attrs.get("FLD_ZONE"),"zone_subtype":attrs.get("ZONE_SUBTY"),"object_id":attrs.get("OBJECTID"),"mapped_geometry":geometry if isinstance(geometry,dict) else None,"geometry_role":"AUTHORITATIVE_GIS_SCREENING_GEOMETRY" if isinstance(geometry,dict) else None,"geometry_definitive":False})
    intersects=bool(evidence)
    return {"status":"SCREENING_COMPLETE","screening_result":"MAPPED_FLOOD_ZONE_INTERSECTION" if intersects else "NO_MAPPED_INTERSECTION_RETURNED","mapped_intersection":intersects,"regulatory_determination":False,"actual_flood_risk_calculated":False,"evidence":evidence,"source":_flood_source(observed_at=observed_at,retrieved=True),"limitations":["Returned FEMA/NJDEP GIS polygon geometry is mapped screening evidence and does not calculate actual flood risk or establish a regulatory flood-hazard boundary.","No mapped intersection returned does not establish that the property is free from flood risk.","This screening does not determine applicability of NJDEP Flood Hazard Area Control Act rules or establish jurisdictional limits.","Site-specific conditions and current State/FEMA mapping must be verified before professional or regulatory reliance."]}


def _validated_parcel_polygon_geometry(geometry: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a conservative WGS84 ArcGIS polygon for screening, or None."""
    if not isinstance(geometry, dict):
        return None
    rings = geometry.get("rings")
    if not isinstance(rings, list) or not rings:
        return None

    valid_rings: list[list[list[float]]] = []
    for ring in rings:
        if not isinstance(ring, list):
            continue
        valid_points: list[list[float]] = []
        for point in ring:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            try:
                x = float(point[0])
                y = float(point[1])
            except (TypeError, ValueError):
                continue
            if -180 <= x <= 180 and -90 <= y <= 90:
                valid_points.append([x, y])
        if len(valid_points) >= 3:
            valid_rings.append(valid_points)

    if not valid_rings:
        return None

    return {
        "rings": valid_rings,
        "spatialReference": {"wkid": 4326},
    }


def screen_njdep_wetlands_parcel_geometry(
    *,
    parcel_geometry: dict[str, Any] | None,
    timeout: float = 20.0,
    post: Callable[..., Any] = httpx.post,
) -> dict[str, Any]:
    """Screen the resolved parcel polygon against NJDEP mapped wetlands.

    The parcel polygon and returned wetlands polygons are reference GIS geometry only.
    This function does not establish surveyed boundaries or regulatory jurisdiction.
    """
    geometry = _validated_parcel_polygon_geometry(parcel_geometry)
    if geometry is None:
        result = _verify("PARCEL_GEOMETRY_NOT_RESOLVED")
        result["screening_basis"] = "PARCEL_GEOMETRY_INTERSECTION"
        return result

    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryPolygon",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "OBJECTID,LABEL12,TYPE12,ACRES",
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "6",
        "f": "json",
    }
    observed_at = _utc_now_iso()
    try:
        response = post(
            NJDEP_WETLANDS_2012_LAYER.rstrip("/") + "/query",
            data=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        result = _verify("NJDEP_WETLANDS_PARCEL_QUERY_FAILED", observed_at=observed_at)
        result["screening_basis"] = "PARCEL_GEOMETRY_INTERSECTION"
        result["error"] = str(exc)
        return result

    if payload.get("error"):
        result = _verify("NJDEP_WETLANDS_PARCEL_QUERY_ERROR", observed_at=observed_at, retrieved=True)
        result["screening_basis"] = "PARCEL_GEOMETRY_INTERSECTION"
        result["error"] = payload["error"]
        return result

    features = payload.get("features")
    if not isinstance(features, list):
        result = _verify("NJDEP_WETLANDS_PARCEL_RESPONSE_INVALID", observed_at=observed_at, retrieved=True)
        result["screening_basis"] = "PARCEL_GEOMETRY_INTERSECTION"
        return result

    evidence = []
    for feature in features:
        attrs = (feature or {}).get("attributes") or {}
        mapped_geometry = (feature or {}).get("geometry")
        evidence.append({
            "label": attrs.get("LABEL12"),
            "type": attrs.get("TYPE12"),
            "acres": attrs.get("ACRES"),
            "object_id": attrs.get("OBJECTID"),
            "mapped_geometry": mapped_geometry if isinstance(mapped_geometry, dict) else None,
            "geometry_role": "AUTHORITATIVE_GIS_SCREENING_GEOMETRY" if isinstance(mapped_geometry, dict) else None,
            "geometry_definitive": False,
        })

    intersects = bool(evidence)
    return {
        "status": "SCREENING_COMPLETE",
        "screening_result": "MAPPED_WETLANDS_INTERSECTION" if intersects else "NO_MAPPED_INTERSECTION_RETURNED",
        "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
        "mapped_intersection": intersects,
        "regulatory_determination": False,
        "evidence": evidence,
        "source": _wetlands_source(observed_at=observed_at, retrieved=True),
        "limitations": [
            "The query used resolved statewide parcel reference geometry, not a surveyed or legal parcel boundary.",
            "Returned wetlands GIS polygon geometry is mapped screening evidence, not a surveyed, definitive, or regulatory wetlands boundary.",
            "No mapped parcel intersection returned does not establish that regulated wetlands are absent.",
            "Dataset vintage and current regulatory applicability must be verified before professional reliance.",
        ],
    }


def screen_njdep_fema_flood_parcel_geometry(
    *,
    parcel_geometry: dict[str, Any] | None,
    timeout: float = 20.0,
    post: Callable[..., Any] = httpx.post,
) -> dict[str, Any]:
    """Screen the resolved parcel polygon against FEMA NFHL polygons published by NJDEP."""
    source = _flood_source()
    geometry = _validated_parcel_polygon_geometry(parcel_geometry)
    if geometry is None:
        return {
            "status": "VERIFY",
            "screening_result": "NOT_ESTABLISHED",
            "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
            "mapped_intersection": None,
            "regulatory_determination": False,
            "actual_flood_risk_calculated": False,
            "reason": "PARCEL_GEOMETRY_NOT_RESOLVED",
            "source": source,
        }

    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryPolygon",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "OBJECTID,FLD_ZONE,ZONE_SUBTY",
        "returnGeometry": "true",
        "outSR": "4326",
        "geometryPrecision": "6",
        "f": "json",
    }
    observed_at = _utc_now_iso()
    try:
        response = post(
            NJDEP_FEMA_NFHL_LAYER.rstrip("/") + "/query",
            data=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {
            "status": "VERIFY",
            "screening_result": "NOT_ESTABLISHED",
            "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
            "mapped_intersection": None,
            "regulatory_determination": False,
            "actual_flood_risk_calculated": False,
            "reason": "NFHL_PARCEL_QUERY_FAILED",
            "error": str(exc),
            "source": _flood_source(observed_at=observed_at),
        }

    if payload.get("error") or not isinstance(payload.get("features"), list):
        return {
            "status": "VERIFY",
            "screening_result": "NOT_ESTABLISHED",
            "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
            "mapped_intersection": None,
            "regulatory_determination": False,
            "actual_flood_risk_calculated": False,
            "reason": "NFHL_PARCEL_RESPONSE_INVALID",
            "error": payload.get("error"),
            "source": _flood_source(observed_at=observed_at, retrieved=True),
        }

    evidence = []
    for feature in payload["features"]:
        attrs = (feature or {}).get("attributes") or {}
        mapped_geometry = (feature or {}).get("geometry")
        evidence.append({
            "flood_zone": attrs.get("FLD_ZONE"),
            "zone_subtype": attrs.get("ZONE_SUBTY"),
            "object_id": attrs.get("OBJECTID"),
            "mapped_geometry": mapped_geometry if isinstance(mapped_geometry, dict) else None,
            "geometry_role": "AUTHORITATIVE_GIS_SCREENING_GEOMETRY" if isinstance(mapped_geometry, dict) else None,
            "geometry_definitive": False,
        })

    intersects = bool(evidence)
    return {
        "status": "SCREENING_COMPLETE",
        "screening_result": "MAPPED_FLOOD_ZONE_INTERSECTION" if intersects else "NO_MAPPED_INTERSECTION_RETURNED",
        "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
        "mapped_intersection": intersects,
        "regulatory_determination": False,
        "actual_flood_risk_calculated": False,
        "evidence": evidence,
        "source": _flood_source(observed_at=observed_at, retrieved=True),
        "limitations": [
            "The query used resolved statewide parcel reference geometry, not a surveyed or legal parcel boundary.",
            "Returned FEMA/NJDEP GIS polygon geometry is mapped screening evidence and does not calculate actual flood risk or establish a regulatory flood-hazard boundary.",
            "No mapped parcel intersection returned does not establish that the property is free from flood risk.",
            "This screening does not determine applicability of NJDEP Flood Hazard Area Control Act rules or establish jurisdictional limits.",
            "Site-specific conditions and current State/FEMA mapping must be verified before professional or regulatory reliance.",
        ],
    }
