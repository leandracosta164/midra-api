"""Generic ArcGIS zoning-map evidence provider.

This provider only extracts parcel-specific evidence from an ArcGIS REST-style
JSON representation that has already been retrieved and supplied as bytes. It
does not fetch URLs, infer districts from map graphics, or decide whether a
source is legally authoritative.
"""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from app.services.zoning_evidence_provider import ZoningEvidenceProvider, ZoningEvidenceRecord


_BLOCK_KEYS = ("block", "block_no", "block_num", "block_number", "parcel_block")
_LOT_KEYS = ("lot", "lot_no", "lot_num", "lot_number", "parcel_lot")
_DISTRICT_KEYS = (
    "zoning_district",
    "zoningdistrict",
    "zoning_zone",
    "zoningzone",
    "zone",
    "district",
    "zone_code",
    "zonecode",
)
_MUNICIPALITY_KEYS = ("municipality", "municipality_name", "muni", "township", "city")


def _norm(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _field(attributes: dict[str, Any], keys: tuple[str, ...]) -> object:
    lowered = {str(key).strip().lower(): value for key, value in attributes.items()}
    for key in keys:
        if key in lowered:
            value = lowered[key]
            if value is not None and str(value).strip():
                return value
    return None


def _is_arcgis_source(source: dict[str, Any]) -> bool:
    if source.get("source_role") != "zoning_map":
        return False
    host = urlparse(str(source.get("source_url") or "")).hostname or ""
    host = host.lower()
    return "arcgis" in host or host.endswith("esri.com")


class ArcGISZoningMapProvider:
    """Extract a district from structured ArcGIS parcel features."""

    def supports(self, source: dict[str, Any]) -> bool:
        return _is_arcgis_source(source)

    def extract(
        self,
        *,
        municipality: str,
        block: str,
        lot: str,
        source: dict[str, Any],
        content: bytes,
    ) -> ZoningEvidenceRecord | None:
        if not self.supports(source):
            return None

        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        features = payload.get("features")
        if not isinstance(features, list):
            return None

        matches: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            attributes = feature.get("attributes")
            if not isinstance(attributes, dict):
                continue

            feature_block = _field(attributes, _BLOCK_KEYS)
            feature_lot = _field(attributes, _LOT_KEYS)
            if _norm(feature_block) != _norm(block) or _norm(feature_lot) != _norm(lot):
                continue

            feature_municipality = _field(attributes, _MUNICIPALITY_KEYS)
            if feature_municipality is not None and _norm(feature_municipality) != _norm(municipality):
                continue

            district = _field(attributes, _DISTRICT_KEYS)
            if district is None:
                continue
            matches.append(attributes)

        # Multiple matching parcel records are ambiguous; never guess.
        if len(matches) != 1:
            return None

        district = str(_field(matches[0], _DISTRICT_KEYS) or "").strip()
        if not district:
            return None

        return ZoningEvidenceRecord(
            municipality=municipality,
            block=str(block),
            lot=str(lot),
            zoning_district=district,
            source=dict(source),
            evidence_type="ARCGIS_PARCEL_FEATURE",
        )
