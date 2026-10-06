"""
MIDRA Engineering
Address & Parcel Intelligence

Authoritative address and parcel resolution for New Jersey.

This module deliberately separates:
1. address geocoding,
2. parcel identification,
3. zoning determination.

It never invents zoning, ownership, entitlement, or development rights.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


GEOCODER_URL = (
    "https://geo.nj.gov/arcgis/rest/services/"
    "Tasks/NJ_Geocode/GeocodeServer/findAddressCandidates"
)

PARCEL_QUERY_URL = (
    "https://maps.nj.gov/arcgis/rest/services/"
    "Framework/Cadastral/MapServer/0/query"
)

REQUEST_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=30.0,
    write=10.0,
    pool=10.0,
)

USER_AGENT = (
    "MIDRA-Engineering-Property-Intelligence/1.0 "
    "(NJ address and parcel resolution)"
)

PARCEL_SEARCH_DISTANCES_METERS = (5, 15, 30, 50)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(
        str(value).strip().upper().split()
    )


def _extract_house_number(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""

    first = text.split()[0]
    digits = ""

    for char in first:
        if char.isdigit():
            digits += char
        else:
            break

    return digits


def _normalize_street(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""

    replacements = {
        "STATE HIGHWAY": "ROUTE",
        "STATE HWY": "ROUTE",
        "HIGHWAY": "ROUTE",
        "HWY": "ROUTE",
        "NJ ROUTE": "ROUTE",
        "NJ-": "ROUTE ",
        "N J ROUTE": "ROUTE",
        "ROAD": "RD",
        "STREET": "ST",
        "AVENUE": "AVE",
        "DRIVE": "DR",
        "BOULEVARD": "BLVD",
        "LANE": "LN",
        "COURT": "CT",
        "PARKWAY": "PKWY",
        "TURNPIKE": "TPKE",
    }

    for source, target in replacements.items():
        text = text.replace(source, target)

    return " ".join(text.split())


def _street_tokens(value: Any) -> set[str]:
    text = _normalize_street(value)
    if not text:
        return set()

    tokens = text.split()
    if tokens and tokens[0].isdigit():
        tokens = tokens[1:]

    return set(tokens)


def _point_in_ring(
    longitude: float,
    latitude: float,
    ring: list[list[float]],
) -> bool:
    if len(ring) < 3:
        return False

    inside = False
    j = len(ring) - 1

    for i in range(len(ring)):
        xi = float(ring[i][0])
        yi = float(ring[i][1])
        xj = float(ring[j][0])
        yj = float(ring[j][1])

        intersects = (
            (yi > latitude) != (yj > latitude)
            and longitude
            < (
                (xj - xi)
                * (latitude - yi)
                / ((yj - yi) or 1e-12)
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def _point_in_parcel_geometry(
    geometry: dict[str, Any],
    *,
    longitude: float,
    latitude: float,
) -> bool:
    rings = geometry.get("rings", [])
    if not rings:
        return False

    return any(
        _point_in_ring(
            longitude,
            latitude,
            ring,
        )
        for ring in rings
        if isinstance(ring, list)
    )


def _request_json(
    url: str,
    params: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers=_headers(),
        ) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json(), None

    except httpx.HTTPError as exc:
        return None, str(exc)

    except ValueError as exc:
        return None, f"Invalid JSON response: {exc}"


def _candidate_to_public(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    location = candidate.get("location") or {}
    attributes = candidate.get("attributes") or {}

    return {
        "match_address": _clean(
            attributes.get("Match_addr")
        ),
        "score": _safe_float(
            candidate.get("score")
        ),
        "status": _clean(
            attributes.get("Status")
        ),
        "city": _clean(
            attributes.get("City")
        ),
        "county": _clean(
            attributes.get("Subregion")
        ),
        "state": _clean(
            attributes.get("Region")
        ),
        "postal_code": _clean(
            attributes.get("Postal")
        ),
        "x": _safe_float(location.get("x")),
        "y": _safe_float(location.get("y")),
    }


def geocode_new_jersey_address(
    address: str,
) -> dict[str, Any]:
    retrieved_at = _utc_now()

    if not address or len(address.strip()) < 3:
        return {
            "status": "INVALID_ADDRESS",
            "address": address,
            "retrieved_at": retrieved_at,
            "candidates": [],
            "selected": None,
            "notes": [
                "Address must contain at least three characters."
            ],
        }

    params = {
        "SingleLine": address.strip(),
        "f": "json",
        "outFields": "*",
        "maxLocations": 8,
        "outSR": 4326,
        "forStorage": "false",
    }

    data, error = _request_json(
        GEOCODER_URL,
        params,
    )

    if data is None:
        return {
            "status": "GEOCODER_ERROR",
            "address": address,
            "retrieved_at": retrieved_at,
            "candidates": [],
            "selected": None,
            "notes": [
                f"NJ statewide geocoder request failed: {error}"
            ],
        }

    candidates = data.get("candidates") or []

    if not candidates:
        return {
            "status": "NO_MATCH",
            "address": address,
            "retrieved_at": retrieved_at,
            "candidates": [],
            "selected": None,
            "notes": [
                "No NJ statewide geocoding candidate was found."
            ],
        }

    normalized = [
        _candidate_to_public(candidate)
        for candidate in candidates
    ]

    normalized.sort(
        key=lambda item: (
            -(item.get("score") or 0),
        )
    )

    selected = normalized[0]
    score = selected.get("score")

    if score is not None and score >= 95:
        status = "HIGH_CONFIDENCE"
    elif score is not None and score >= 85:
        status = "GOOD_MATCH"
    elif score is not None and score >= 70:
        status = "REVIEW_MATCH"
    else:
        status = "LOW_CONFIDENCE"

    return {
        "status": status,
        "address": address,
        "retrieved_at": retrieved_at,
        "candidates": normalized,
        "selected": selected,
        "source": {
            "source_type": "NJ Office of GIS",
            "service": "NJ_Geocode",
            "url": GEOCODER_URL,
            "authoritative": True,
        },
        "notes": [
            (
                "Address resolution uses the New Jersey "
                "statewide geocoding service."
            )
        ],
    }


def suggest_new_jersey_addresses(
    query: str,
) -> dict[str, Any]:
    """
    Lightweight autocomplete endpoint backed by the same
    authoritative NJ statewide geocoder used for final resolution.
    """
    query = (query or "").strip()

    if len(query) < 3:
        return {
            "status": "QUERY_TOO_SHORT",
            "query": query,
            "suggestions": [],
        }

    result = geocode_new_jersey_address(query)

    suggestions = []

    for candidate in result.get("candidates") or []:
        address = candidate.get("match_address")
        if not address:
            continue

        suggestions.append(
            {
                "address": address,
                "score": candidate.get("score"),
                "city": candidate.get("city"),
                "county": candidate.get("county"),
                "state": candidate.get("state"),
                "postal_code": candidate.get(
                    "postal_code"
                ),
                "x": candidate.get("x"),
                "y": candidate.get("y"),
            }
        )

    return {
        "status": result.get("status"),
        "query": query,
        "suggestions": suggestions[:6],
    }


def parse_new_jersey_parcel_query(query: str) -> dict[str, str] | None:
    """Parse user-facing block/lot search text without inventing parcel identity."""
    import re

    text = " ".join((query or "").strip().split())
    if not text:
        return None

    explicit = re.match(
        r"^(?:(?P<municipality>.+?)\s*,?\s+)?(?:block|blk)\s*[:#]?\s*"
        r"(?P<block>[A-Za-z0-9.\-]+)\s*(?:,|\s)+\s*(?:lot|lt)\s*[:#]?\s*"
        r"(?P<lot>[A-Za-z0-9.\-]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if explicit:
        result = {
            "block": explicit.group("block"),
            "lot": explicit.group("lot"),
        }
        municipality = _clean(explicit.group("municipality"))
        if municipality:
            result["municipality"] = municipality
        return result

    compact = re.match(
        r"^(?P<block>[A-Za-z0-9.\-]+)\s*/\s*(?P<lot>[A-Za-z0-9.\-]+)$",
        text,
    )
    if compact:
        return {
            "block": compact.group("block"),
            "lot": compact.group("lot"),
        }

    return None


def _sql_literal(value: Any) -> str:
    return str(value or "").replace("'", "''")


def _parcel_centroid(parcel: dict[str, Any]) -> dict[str, float] | None:
    centroid = parcel.get("centroid") or {}
    x = _safe_float(centroid.get("x"))
    y = _safe_float(centroid.get("y"))
    if x is not None and y is not None:
        return {"longitude": x, "latitude": y}

    geometry = parcel.get("geometry") or {}
    points = [
        point
        for ring in geometry.get("rings") or []
        if isinstance(ring, list)
        for point in ring
        if isinstance(point, list) and len(point) >= 2
    ]
    if not points:
        return None

    xs = [_safe_float(point[0]) for point in points]
    ys = [_safe_float(point[1]) for point in points]
    xs = [x for x in xs if x is not None]
    ys = [y for y in ys if y is not None]
    if not xs or not ys:
        return None
    return {
        "longitude": sum(xs) / len(xs),
        "latitude": sum(ys) / len(ys),
    }


def _parcel_display_label(parcel: dict[str, Any]) -> str:
    street = _clean(parcel.get("street_address")) or _clean(parcel.get("property_location"))
    municipality = _clean(parcel.get("municipality"))
    block = _clean(parcel.get("block"))
    lot = _clean(parcel.get("lot"))

    if street:
        parts = [street, municipality, "NJ"]
        return ", ".join(part for part in parts if part)

    reference = " ".join(
        part for part in [
            f"Block {block}" if block else None,
            f"Lot {lot}" if lot else None,
        ]
        if part
    )
    parts = [reference, municipality, "NJ"]
    return ", ".join(part for part in parts if part)


def parse_new_jersey_parcel_search_query(query: str) -> dict[str, str] | None:
    """Parse exact and safe municipal parcel-discovery text.

    Exact Block/Lot syntax retains the existing contract. Broader discovery is
    allowed only when a municipality and block are both supplied; MIDRA does
    not issue unbounded statewide parcel browsing queries from partial text.
    """
    import re

    exact = parse_new_jersey_parcel_query(query)
    if exact:
        return {**exact, "search_mode": "EXACT_BLOCK_LOT"}

    text = " ".join((query or "").strip().split())
    if not text:
        return None

    municipal_compact = re.match(
        r"^(?P<municipality>.+?)\s+(?P<block>[A-Za-z0-9.\-]+)\s*/\s*(?P<lot>[A-Za-z0-9.\-]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if municipal_compact:
        municipality = _clean(municipal_compact.group("municipality"))
        if municipality:
            return {
                "municipality": municipality,
                "block": municipal_compact.group("block"),
                "lot": municipal_compact.group("lot"),
                "search_mode": "EXACT_BLOCK_LOT",
            }

    municipal_block = re.match(
        r"^(?P<municipality>.+?)\s*,?\s+(?:block|blk)\s*[:#]?\s*(?P<block>[A-Za-z0-9.\-]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if municipal_block:
        municipality = _clean(municipal_block.group("municipality"))
        if municipality:
            return {
                "municipality": municipality,
                "block": municipal_block.group("block"),
                "search_mode": "MUNICIPAL_BLOCK_DISCOVERY",
            }

    return None


def _municipality_search_tokens(value: str) -> list[str]:
    import re

    stop = {"CITY", "TOWNSHIP", "TWP", "BOROUGH", "BORO", "TOWN", "VILLAGE", "OF"}
    tokens = [
        token
        for token in re.findall(r"[A-Z0-9]+", _normalize_text(value))
        if token not in stop
    ]
    return tokens[:4]


def _query_parcels_by_municipal_block(
    *,
    municipality: str,
    block: str,
) -> dict[str, Any]:
    """Query a bounded municipal block from the authoritative statewide parcel layer."""
    municipality_tokens = _municipality_search_tokens(municipality)
    if not municipality_tokens:
        return {
            "status": "PARCEL_QUERY_UNSAFE",
            "features": [],
            "notes": ["Municipality is required for partial block parcel discovery."],
        }

    clauses = [f"PCLBLOCK = '{_sql_literal(block)}'"]
    clauses.extend(
        f"UPPER(MUN_NAME) LIKE '%{_sql_literal(token)}%'"
        for token in municipality_tokens
    )
    params = {
        "f": "json",
        "where": " AND ".join(clauses),
        "outFields": PARCEL_OUT_FIELDS,
        "returnGeometry": "true",
        "returnCentroid": "true",
        "outSR": "4326",
        "resultRecordCount": 250,
        "orderByFields": "MUN_NAME ASC, PCLBLOCK ASC, PCLLOT ASC, OBJECTID ASC",
    }
    data, error = _request_json(PARCEL_QUERY_URL, params)
    if data is None:
        return {
            "status": "PARCEL_SERVICE_ERROR",
            "features": [],
            "notes": [f"NJ parcel service request failed: {error}"],
        }
    if "error" in data:
        return {
            "status": "PARCEL_QUERY_ERROR",
            "features": [],
            "notes": [str(data["error"])],
        }
    features = data.get("features") or []
    return {
        "status": "PARCELS_FOUND" if features else "NO_PARCELS_FOUND",
        "features": features,
        "notes": [],
    }


def _query_parcels_by_block_lot(
    *,
    block: str,
    lot: str,
) -> dict[str, Any]:
    params = {
        "f": "json",
        "where": (
            f"PCLBLOCK = '{_sql_literal(block)}' "
            f"AND PCLLOT = '{_sql_literal(lot)}'"
        ),
        "outFields": PARCEL_OUT_FIELDS,
        "returnGeometry": "true",
        "returnCentroid": "true",
        "outSR": "4326",
        "resultRecordCount": 100,
        "orderByFields": "MUN_NAME ASC, OBJECTID ASC",
    }
    data, error = _request_json(PARCEL_QUERY_URL, params)
    if data is None:
        return {
            "status": "PARCEL_SERVICE_ERROR",
            "features": [],
            "notes": [f"NJ parcel service request failed: {error}"],
        }
    if "error" in data:
        return {
            "status": "PARCEL_QUERY_ERROR",
            "features": [],
            "notes": [str(data["error"])],
        }
    features = data.get("features") or []
    return {
        "status": "PARCELS_FOUND" if features else "NO_PARCELS_FOUND",
        "features": features,
        "notes": [],
    }


def suggest_new_jersey_parcels(query: str) -> dict[str, Any]:
    """Suggest authoritative statewide NJ parcel identities from exact or bounded municipal text."""
    parsed = parse_new_jersey_parcel_search_query(query)
    if not parsed:
        return {
            "status": "QUERY_NOT_PARCEL",
            "query": (query or "").strip(),
            "suggestions": [],
        }

    if parsed.get("search_mode") == "MUNICIPAL_BLOCK_DISCOVERY":
        result = _query_parcels_by_municipal_block(
            municipality=parsed["municipality"],
            block=parsed["block"],
        )
    else:
        result = _query_parcels_by_block_lot(
            block=parsed["block"],
            lot=parsed["lot"],
        )
    municipality_filter = _normalize_text(parsed.get("municipality"))
    municipality_tokens = _municipality_search_tokens(parsed.get("municipality") or "")
    suggestions: list[dict[str, Any]] = []

    for feature in result.get("features") or []:
        parcel = _normalize_parcel(feature)
        if municipality_filter:
            municipality = _normalize_text(parcel.get("municipality"))
            candidate_tokens = set(_municipality_search_tokens(municipality))
            if municipality_tokens and not all(token in candidate_tokens for token in municipality_tokens):
                continue
            if not municipality_tokens and municipality_filter not in municipality:
                continue

        suggestions.append(
            {
                "object_id": parcel.get("object_id"),
                "label": _parcel_display_label(parcel),
                "municipality": parcel.get("municipality"),
                "county": parcel.get("county"),
                "block": parcel.get("block"),
                "lot": parcel.get("lot"),
                "qualifier": parcel.get("qualifier"),
                "street_address": parcel.get("street_address"),
                "property_location": parcel.get("property_location"),
                "centroid": _parcel_centroid(parcel),
                "source": {
                    "source_type": "NJ Office of GIS",
                    "service": "Statewide Parcels",
                    "url": PARCEL_QUERY_URL,
                    "authoritative": True,
                },
            }
        )

    return {
        "status": result.get("status"),
        "query": (query or "").strip(),
        "parsed": parsed,
        "suggestions": suggestions[:12],
    }


def resolve_new_jersey_parcel_object_id(
    object_id: int,
    *,
    requested_label: str | None = None,
) -> dict[str, Any]:
    """Resolve one exact statewide parcel feature without geocoding an address."""
    resolved_at = _utc_now()
    params = {
        "f": "json",
        "where": f"OBJECTID = {int(object_id)}",
        "outFields": PARCEL_OUT_FIELDS,
        "returnGeometry": "true",
        "returnCentroid": "true",
        "outSR": "4326",
        "resultRecordCount": 1,
    }
    data, error = _request_json(PARCEL_QUERY_URL, params)
    if data is None:
        return {
            "status": "PARCEL_SERVICE_ERROR",
            "requested_address": requested_label or f"Parcel OBJECTID {object_id}",
            "resolved_at": resolved_at,
            "parcel": None,
            "municipality": None,
            "county": None,
            "coordinates": None,
            "verification_items": [f"NJ statewide parcel lookup failed: {error}"],
        }

    features = data.get("features") or []
    if not features:
        return {
            "status": "PARCEL_NOT_RESOLVED",
            "requested_address": requested_label or f"Parcel OBJECTID {object_id}",
            "resolved_at": resolved_at,
            "parcel": None,
            "municipality": None,
            "county": None,
            "coordinates": None,
            "verification_items": [
                "The selected statewide parcel feature could not be resolved."
            ],
        }

    parcel = _normalize_parcel(features[0])
    label = requested_label or _parcel_display_label(parcel)
    coordinates = _parcel_centroid(parcel)

    return {
        "status": "PROPERTY_RESOLVED",
        "requested_address": label,
        "resolved_at": resolved_at,
        "matched_address": _parcel_display_label(parcel),
        "match_score": 100,
        "coordinates": coordinates,
        "municipality": parcel.get("municipality"),
        "county": parcel.get("county"),
        "state": "New Jersey",
        "parcel": parcel,
        "geocoding": {
            "status": "NOT_USED_PARCEL_IDENTITY",
            "source": None,
        },
        "parcel_source": {
            "source_type": "NJ Office of GIS",
            "service": "Statewide Parcels",
            "url": PARCEL_QUERY_URL,
            "authoritative": True,
        },
        "parcel_match": {
            "status": "PARCEL_OBJECT_ID_RESOLVED",
            "match_score": 100,
            "candidate_count": 1,
            "search_distance_meters": None,
            "identity_evidence": {
                "basis": "authoritative_statewide_parcel_object_id",
                "block": parcel.get("block"),
                "lot": parcel.get("lot"),
                "municipality": parcel.get("municipality"),
                "parcel_object_id": parcel.get("object_id"),
            },
        },
        "verification_items": [
            "Parcel identity was resolved directly from the NJ Office of GIS statewide parcel layer.",
            "The zoning district still requires a separate authoritative zoning-map lookup.",
        ],
        "notes": [
            "Direct parcel resolution does not determine zoning.",
            "Direct parcel resolution does not determine legal ownership or development entitlement.",
        ],
    }


PARCEL_OUT_FIELDS = (
    "OBJECTID,"
    "PAMS_PIN,"
    "PCL_MUN,"
    "PCLBLOCK,"
    "PCLLOT,"
    "PCLQCODE,"
    "PCLLASTUPD,"
    "PIN_NODUP,"
    "COUNTY,"
    "MUN_NAME,"
    "CD_CODE,"
    "PROP_CLASS,"
    "PROP_LOC,"
    "ST_ADDRESS,"
    "CITY_STATE,"
    "ZIP_CODE,"
    "ZIP5,"
    "ZIP_PLUS4,"
    "GIS_PIN,"
    "PROP_USE,"
    "BLDG_DESC,"
    "LAND_DESC,"
    "CALC_ACRE,"
    "PCL_GUID,"
    "PCL_PBDATE,"
    "SHAPE_Area,"
    "SHAPE_Length"
)


def _normalize_parcel(
    feature: dict[str, Any],
) -> dict[str, Any]:
    attributes = feature.get("attributes") or {}
    geometry = feature.get("geometry") or {}

    return {
        "object_id": attributes.get("OBJECTID"),
        "pams_pin": _clean(attributes.get("PAMS_PIN")),
        "gis_pin": _clean(attributes.get("GIS_PIN")),
        "pin_no_duplicate": _clean(
            attributes.get("PIN_NODUP")
        ),
        "municipality_code": _clean(
            attributes.get("PCL_MUN")
        ),
        "municipality": _clean(
            attributes.get("MUN_NAME")
        ),
        "county": _clean(attributes.get("COUNTY")),
        "block": _clean(attributes.get("PCLBLOCK")),
        "lot": _clean(attributes.get("PCLLOT")),
        "qualifier": _clean(
            attributes.get("PCLQCODE")
        ),
        "property_class": _clean(
            attributes.get("PROP_CLASS")
        ),
        "property_location": _clean(
            attributes.get("PROP_LOC")
        ),
        "street_address": _clean(
            attributes.get("ST_ADDRESS")
        ),
        "city_state": _clean(
            attributes.get("CITY_STATE")
        ),
        "zip_code": _clean(
            attributes.get("ZIP_CODE")
        ),
        "zip5": _clean(attributes.get("ZIP5")),
        "zip_plus4": _clean(
            attributes.get("ZIP_PLUS4")
        ),
        "acreage": _safe_float(
            attributes.get("CALC_ACRE")
        ),
        "property_use": _clean(
            attributes.get("PROP_USE")
        ),
        "building_description": _clean(
            attributes.get("BLDG_DESC")
        ),
        "land_description": _clean(
            attributes.get("LAND_DESC")
        ),
        "parcel_guid": _clean(
            attributes.get("PCL_GUID")
        ),
        "parcel_publication_date": attributes.get(
            "PCL_PBDATE"
        ),
        "shape_area": _safe_float(
            attributes.get("SHAPE_Area")
        ),
        "shape_length": _safe_float(
            attributes.get("SHAPE_Length")
        ),
        "centroid": feature.get("centroid") or {},
        "geometry": geometry,
    }


def _query_parcels(
    *,
    longitude: float,
    latitude: float,
    distance_meters: float,
) -> dict[str, Any]:
    params = {
        "f": "json",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": distance_meters,
        "units": "esriSRUnit_Meter",
        "outFields": PARCEL_OUT_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "returnTrueCurves": "false",
        "returnCentroid": "true",
        "resultRecordCount": 25,
        "orderByFields": "OBJECTID ASC",
    }

    data, error = _request_json(
        PARCEL_QUERY_URL,
        params,
    )

    if data is None:
        return {
            "status": "PARCEL_SERVICE_ERROR",
            "features": [],
            "notes": [
                f"NJ parcel service request failed: {error}"
            ],
        }

    if "error" in data:
        return {
            "status": "PARCEL_QUERY_ERROR",
            "features": [],
            "notes": [str(data["error"])],
        }

    features = data.get("features") or []

    return {
        "status": (
            "PARCELS_FOUND"
            if features
            else "NO_PARCELS_FOUND"
        ),
        "features": features,
        "notes": [],
    }


def _score_parcel(
    feature: dict[str, Any],
    *,
    geocoded_city: str | None,
    geocoded_zip: str | None,
    geocoded_address: str | None,
    longitude: float | None = None,
    latitude: float | None = None,
    search_distance_meters: float | None = None,
) -> int:
    parcel = _normalize_parcel(feature)
    score = 0

    parcel_address = _normalize_text(
        parcel.get("street_address")
    )
    parcel_location = _normalize_text(
        parcel.get("property_location")
    )
    parcel_city = _normalize_text(
        parcel.get("city_state")
    )
    parcel_zip = _normalize_text(
        parcel.get("zip5")
    )

    target_address = _normalize_text(
        geocoded_address
    )
    target_city = _normalize_text(
        geocoded_city
    )
    target_zip = _normalize_text(
        geocoded_zip
    )

    target_house = _extract_house_number(
        target_address
    )
    parcel_house = _extract_house_number(
        parcel_address
    )
    location_house = _extract_house_number(
        parcel_location
    )

    # ZIP is useful, but is never sufficient by itself.
    if target_zip and parcel_zip and target_zip == parcel_zip:
        score += 20

    # Postal city and GIS/tax municipality can differ.
    # Therefore a mismatch is deliberately NOT penalized.
    if target_city and parcel_city and target_city in parcel_city:
        score += 10

    if target_house and (
        target_house == parcel_house
        or target_house == location_house
    ):
        score += 20

    target_streets = _street_tokens(target_address)
    parcel_streets = (
        _street_tokens(parcel_address)
        | _street_tokens(parcel_location)
    )

    if target_streets and parcel_streets:
        if target_streets & parcel_streets:
            score += 20

    # Strongest possible spatial evidence.
    if (
        longitude is not None
        and latitude is not None
        and _point_in_parcel_geometry(
            parcel.get("geometry") or {},
            longitude=longitude,
            latitude=latitude,
        )
    ):
        score += 35

    # Controlled proximity helps when the geocoder point lands
    # on a roadway, driveway, or frontage.
    if search_distance_meters is not None:
        if search_distance_meters <= 5:
            score += 20
        elif search_distance_meters <= 15:
            score += 15
        elif search_distance_meters <= 30:
            score += 8

    if parcel.get("pams_pin"):
        score += 5

    if parcel.get("block") and parcel.get("lot"):
        score += 5

    return min(score, 100)


def find_parcel_by_point(
    longitude: float,
    latitude: float,
    *,
    geocoded_city: str | None = None,
    geocoded_zip: str | None = None,
    geocoded_address: str | None = None,
) -> dict[str, Any]:
    retrieved_at = _utc_now()
    all_candidates: list[dict[str, Any]] = []

    for distance in PARCEL_SEARCH_DISTANCES_METERS:
        result = _query_parcels(
            longitude=longitude,
            latitude=latitude,
            distance_meters=distance,
        )

        if result["status"] in {
            "PARCEL_SERVICE_ERROR",
            "PARCEL_INVALID_RESPONSE",
            "PARCEL_QUERY_ERROR",
        }:
            return {
                "status": result["status"],
                "retrieved_at": retrieved_at,
                "parcel": None,
                "notes": result.get("notes", []),
            }

        features = result.get("features") or []

        if not features:
            continue

        for feature in features:
            normalized = _normalize_parcel(feature)

            candidate_score = _score_parcel(
                feature,
                geocoded_city=geocoded_city,
                geocoded_zip=geocoded_zip,
                geocoded_address=geocoded_address,
                longitude=longitude,
                latitude=latitude,
                search_distance_meters=distance,
            )

            all_candidates.append(
                {
                    "score": candidate_score,
                    "search_distance_meters": distance,
                    "parcel": normalized,
                }
            )

        # A polygon containing the geocoded point is excellent
        # evidence. Otherwise we continue expanding the radius
        # because road-address points can fall outside parcels.
        if any(
            candidate["score"] >= 75
            and candidate["search_distance_meters"] <= 15
            for candidate in all_candidates
        ):
            break

    if not all_candidates:
        return {
            "status": "NO_PARCEL_MATCH",
            "retrieved_at": retrieved_at,
            "parcel": None,
            "notes": [
                (
                    "No statewide parcel polygon was found "
                    "within the controlled search distances."
                )
            ],
        }

    all_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["search_distance_meters"],
        )
    )

    best = all_candidates[0]
    best_score = best["score"]

    # 40 is intentionally conservative enough to require more
    # than a bare ZIP/proximity coincidence, while allowing a
    # commercial property whose postal city differs from its
    # tax/GIS municipality.
    if best_score < 40:
        return {
            "status": "PARCEL_MATCH_REQUIRES_REVIEW",
            "retrieved_at": retrieved_at,
            "parcel": None,
            "match_score": best_score,
            "candidates": all_candidates[:10],
            "notes": [
                (
                    "Nearby parcels were found, but the available "
                    "address, street, ZIP and spatial evidence did "
                    "not provide sufficient confidence to assign "
                    "one automatically."
                ),
                "MIDRA will not guess the parcel.",
            ],
        }

    return {
        "status": "PARCEL_FOUND",
        "retrieved_at": retrieved_at,
        "parcel": best["parcel"],
        "match_score": best_score,
        "search_distance_meters": (
            best["search_distance_meters"]
        ),
        "candidate_count": len(all_candidates),
        "identity_evidence": _build_parcel_identity_evidence(
            best["parcel"],
            geocoded_city=geocoded_city,
            geocoded_zip=geocoded_zip,
            geocoded_address=geocoded_address,
            search_distance_meters=(
                best["search_distance_meters"]
            ),
            match_score=best_score,
        ),
        "source": {
            "source_type": "NJ Office of GIS",
            "service": (
                "Parcels and MOD-IV Composite of New Jersey"
            ),
            "url": PARCEL_QUERY_URL,
            "authoritative": True,
        },
        "notes": [
            (
                "Parcel was identified using the NJ Office "
                "of GIS statewide parcel layer."
            ),
            (
                "Postal municipality and GIS/tax municipality "
                "are allowed to differ."
            ),
        ],
    }


def resolve_new_jersey_property(
    address: str,
) -> dict[str, Any]:
    resolved_at = _utc_now()

    geocode = geocode_new_jersey_address(address)
    selected = geocode.get("selected")

    if not selected:
        return {
            "status": "ADDRESS_NOT_RESOLVED",
            "requested_address": address,
            "resolved_at": resolved_at,
            "geocoding": geocode,
            "parcel": None,
            "municipality": None,
            "county": None,
            "coordinates": None,
            "verification_items": [
                (
                    "The address could not be confidently "
                    "resolved using the NJ statewide geocoder."
                ),
                (
                    "Parcel and zoning analysis cannot be "
                    "considered property-specific until the "
                    "address is resolved."
                ),
            ],
        }

    longitude = selected.get("x")
    latitude = selected.get("y")

    if longitude is None or latitude is None:
        return {
            "status": "GEOCODE_NO_COORDINATES",
            "requested_address": address,
            "resolved_at": resolved_at,
            "geocoding": geocode,
            "parcel": None,
            "municipality": None,
            "county": None,
            "coordinates": None,
            "verification_items": [
                (
                    "The NJ geocoder returned a candidate "
                    "without usable coordinates."
                )
            ],
        }

    parcel_result = find_parcel_by_point(
        longitude=longitude,
        latitude=latitude,
        geocoded_city=selected.get("city"),
        geocoded_zip=selected.get("postal_code"),
        geocoded_address=selected.get("match_address"),
    )

    parcel = parcel_result.get("parcel")

    if not parcel:
        return {
            "status": (
                "ADDRESS_RESOLVED_PARCEL_NOT_FOUND"
                if parcel_result.get("status") == "NO_PARCEL_MATCH"
                else parcel_result.get(
                    "status",
                    "ADDRESS_RESOLVED_PARCEL_REVIEW",
                )
            ),
            "requested_address": address,
            "resolved_at": resolved_at,
            "matched_address": selected.get("match_address"),
            "match_score": selected.get("score"),
            "geocoding": geocode,
            "parcel": None,
            "municipality": selected.get("city"),
            "county": selected.get("county"),
            "coordinates": {
                "longitude": longitude,
                "latitude": latitude,
            },
            "parcel_match": parcel_result,
            "verification_items": [
                (
                    "The address was successfully geocoded, "
                    "but a sufficiently supported parcel "
                    "could not yet be assigned."
                ),
                (
                    "Parcel-specific zoning analysis should "
                    "not proceed until the parcel is confirmed."
                ),
            ],
        }

    # IMPORTANT:
    # For commercial properties the postal city can differ from
    # the tax/GIS municipality. The parcel municipality is therefore
    # authoritative for downstream zoning resolution.
    municipality = (
        parcel.get("municipality")
        or selected.get("city")
    )
    county = (
        parcel.get("county")
        or selected.get("county")
    )

    return {
        "status": "PROPERTY_RESOLVED",
        "requested_address": address,
        "resolved_at": resolved_at,
        "matched_address": selected.get("match_address"),
        "match_score": selected.get("score"),
        "coordinates": {
            "longitude": longitude,
            "latitude": latitude,
        },
        "municipality": municipality,
        "county": county,
        "state": selected.get("state") or "New Jersey",
        "parcel": parcel,
        "geocoding": {
            "status": geocode.get("status"),
            "source": geocode.get("source"),
        },
        "parcel_source": parcel_result.get("source"),
        "parcel_match": {
            "match_score": parcel_result.get("match_score"),
            "search_distance_meters": parcel_result.get(
                "search_distance_meters"
            ),
            "candidate_count": parcel_result.get(
                "candidate_count"
            ),
            "status": parcel_result.get("status"),
            "identity_evidence": parcel_result.get(
                "identity_evidence"
            ),
        },
        "verification_items": [
            (
                "Parcel identity is based on the NJ Office "
                "of GIS statewide geocoder and parcel layer."
            ),
            (
                "The parcel municipality is used for downstream "
                "zoning even when the postal city differs."
            ),
            (
                "The zoning district still requires a separate "
                "authoritative zoning-map lookup."
            ),
        ],
        "notes": [
            "This resolver does not determine zoning.",
            (
                "This resolver does not determine legal ownership "
                "or development entitlement."
            ),
        ],
    }

def _build_parcel_identity_evidence(
    parcel: dict[str, Any],
    *,
    geocoded_city: str | None,
    geocoded_zip: str | None,
    geocoded_address: str | None,
    search_distance_meters: float | None,
    match_score: int,
) -> dict[str, Any]:
    """
    Describe parcel identity evidence without treating tax-record
    descriptive fields as authoritative proof of the requested address.

    This is intentionally evidence-oriented. It does not manufacture
    an address match when the parcel record contains contradictory
    address fields.
    """
    parcel_location = str(
        parcel.get("property_location") or ""
    ).strip()

    parcel_street = str(
        parcel.get("street_address") or ""
    ).strip()

    parcel_city_state = str(
        parcel.get("city_state") or ""
    ).strip()

    parcel_zip = str(
        parcel.get("zip_code")
        or parcel.get("zip5")
        or ""
    ).strip()

    requested_city = str(
        geocoded_city or ""
    ).strip()

    requested_zip = str(
        geocoded_zip or ""
    ).strip()

    address_text = str(
        geocoded_address or ""
    ).strip()

    conflicting_address_fields = []

    if requested_zip and parcel_zip and requested_zip != parcel_zip:
        conflicting_address_fields.append(
            "parcel ZIP differs from geocoder ZIP"
        )

    if (
        requested_city
        and parcel_city_state
        and requested_city.lower()
        not in parcel_city_state.lower()
    ):
        conflicting_address_fields.append(
            "parcel city/state differs from geocoder city"
        )

    if parcel_location and address_text:
        requested_normalized = (
            address_text.upper()
            .replace("STATE HIGHWAY", "ROUTE")
            .replace("HIGHWAY", "ROUTE")
        )

        parcel_normalized = (
            parcel_location.upper()
            .replace("STATE HIGHWAY", "ROUTE")
            .replace("HIGHWAY", "ROUTE")
        )

        if (
            parcel_normalized
            and parcel_normalized not in requested_normalized
            and requested_normalized
            and requested_normalized not in parcel_normalized
        ):
            conflicting_address_fields.append(
                "parcel property-location text differs from geocoder address"
            )

    return {
        "match_score": match_score,
        "search_distance_meters": search_distance_meters,
        "geocoder_address": address_text or None,
        "geocoder_city": requested_city or None,
        "geocoder_zip": requested_zip or None,
        "parcel_property_location": parcel_location or None,
        "parcel_street_address": parcel_street or None,
        "parcel_city_state": parcel_city_state or None,
        "parcel_zip": parcel_zip or None,
        "address_field_conflicts": conflicting_address_fields,
        "address_field_conflict": bool(
            conflicting_address_fields
        ),
        "geometry_proximity_available": (
            search_distance_meters is not None
        ),
        "identity_status": (
            "CONTRADICTORY_ADDRESS_FIELDS"
            if conflicting_address_fields
            else "CONSISTENT_ADDRESS_FIELDS"
        ),
    }



