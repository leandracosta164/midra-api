"""Property map intelligence for zoning-map and tax-map artifacts.

This layer is additive: it resolves map artifacts from already-discovered source
records without changing zoning promotion, legal-control, or parcel resolution.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _is_http(url: str) -> bool:
    return urlparse(str(url or "")).scheme in {"http", "https"}


def _source_url(source: dict[str, Any]) -> str:
    return str(source.get("source_url") or source.get("url") or "").strip()


def _label(source: dict[str, Any]) -> str:
    return str(source.get("label") or source.get("title") or "").strip()


def _official(source: dict[str, Any]) -> bool:
    return bool(
        source.get("municipal_official_link_verified") is True
        or source.get("authority_verified") is True
        or source.get("authoritative") is True
    )


def _artifact(source: dict[str, Any], *, map_type: str, reason: str) -> dict[str, Any]:
    url = _source_url(source)
    return {
        "status": "RESOLVED",
        "map_type": map_type,
        "label": _label(source),
        "source_url": url,
        "official_source_verified": _official(source),
        "reason": reason,
        "source": source,
    }


def resolve_zoning_map(
    *,
    municipality: str,
    sources: list[dict[str, Any]],
    zoning_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the best explicit zoning-map artifact already known to MIDRA."""
    candidates: list[tuple[int, dict[str, Any]]] = []
    for source in sources or []:
        url = _source_url(source)
        if not _is_http(url):
            continue
        label_text = _norm(_label(source))
        role_text = _norm(source.get("source_role"))
        url_text = _norm(url)

        zoning_map_signal = bool(
            "zoning map" in label_text
            or "zoning-map" in url_text
            or "zoning_map" in url_text
            or role_text == "zoning_map"
            or (
                ("arcgis" in url_text or "featureserver" in url_text or "mapserver" in url_text)
                and ("zoning" in label_text or "zoning" in url_text or role_text == "zoning_map")
            )
        )
        if not zoning_map_signal:
            continue

        score = 0
        if "zoning map" in label_text or "zoning-map" in url_text or "zoning_map" in url_text:
            score += 100
        if role_text == "zoning_map":
            score += 80
        if "arcgis" in url_text or "featureserver" in url_text or "mapserver" in url_text:
            score += 20
        if _official(source):
            score += 40
        candidates.append((score, source))

    if not candidates:
        return {
            "status": "VERIFY",
            "map_type": "ZONING_MAP",
            "municipality": municipality,
            "reason": "NO_EXPLICIT_ZONING_MAP_SOURCE",
        }

    candidates.sort(key=lambda item: item[0], reverse=True)
    result = _artifact(candidates[0][1], map_type="ZONING_MAP", reason="EXPLICIT_ZONING_MAP_SOURCE")
    zoning = zoning_result or {}
    candidate = zoning.get("candidate") or {}
    record = candidate.get("record") or {}
    result["zoning_district"] = record.get("zoning_district")
    result["parcel_intersection_verified"] = bool(
        candidate.get("status") == "ZONING_CANDIDATE_RESOLVED"
        or record.get("evidence") == "ARCGIS_SPATIAL_INTERSECTION"
    )
    return result


def resolve_tax_map(
    *,
    municipality: str,
    block: str,
    lot: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve an explicit tax-map artifact and sheet only when evidence says so.

    The resolver never guesses a sheet number from block/lot.  A sheet is returned
    only when source metadata explicitly identifies the requested block/lot or an
    already-resolved tax_map_sheet value is present.
    """
    candidates: list[tuple[int, dict[str, Any]]] = []
    block_n = _norm(block)
    lot_n = _norm(lot)

    for source in sources or []:
        url = _source_url(source)
        if not _is_http(url):
            continue
        label_text = _norm(_label(source))
        role_text = _norm(source.get("source_role"))
        url_text = _norm(url)
        tax_map_signal = bool(
            "tax map" in label_text
            or "tax map" in url_text
            or "taxmap" in url_text
            or role_text == "tax_map"
        )
        if not tax_map_signal:
            continue

        score = 0
        if "tax map" in label_text or "tax map" in url_text or "taxmap" in url_text:
            score += 100
        if role_text == "tax_map":
            score += 80
        if _official(source):
            score += 40

        source_block = _norm(source.get("block"))
        source_lot = _norm(source.get("lot"))
        if block_n and source_block == block_n:
            score += 30
            if lot_n and source_lot == lot_n:
                score += 30

        if score:
            candidates.append((score, source))

    if not candidates:
        return {
            "status": "VERIFY",
            "map_type": "TAX_MAP",
            "municipality": municipality,
            "block": str(block),
            "lot": str(lot),
            "reason": "NO_EXPLICIT_TAX_MAP_SOURCE",
        }

    candidates.sort(key=lambda item: item[0], reverse=True)
    source = candidates[0][1]
    result = _artifact(source, map_type="TAX_MAP", reason="EXPLICIT_TAX_MAP_SOURCE")
    result.update({"block": str(block), "lot": str(lot)})

    sheet = source.get("tax_map_sheet") or source.get("sheet")
    if sheet not in (None, ""):
        result["tax_map_sheet"] = str(sheet)
        result["sheet_status"] = "RESOLVED"
    else:
        result["tax_map_sheet"] = None
        result["sheet_status"] = "VERIFY"
        result["sheet_reason"] = "TAX_MAP_SHEET_NOT_EXPLICITLY_RESOLVED"
    return result


def resolve_property_maps(
    *,
    municipality: str,
    block: str,
    lot: str,
    sources: list[dict[str, Any]],
    zoning_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return independent zoning-map and tax-map artifacts for a property."""
    return {
        "status": "PROPERTY_MAP_ANALYSIS_COMPLETE",
        "municipality": municipality,
        "block": str(block),
        "lot": str(lot),
        "zoning_map": resolve_zoning_map(
            municipality=municipality,
            sources=sources,
            zoning_result=zoning_result,
        ),
        "tax_map": resolve_tax_map(
            municipality=municipality,
            block=block,
            lot=lot,
            sources=sources,
        ),
    }
