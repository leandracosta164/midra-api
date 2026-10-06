"""Discover ArcGIS web-map and feature-service references from app metadata."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


_ARCGIS_ITEM_ID = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)
_SERVICE_URL_KEYS = {"url", "serviceUrl", "featureServiceUrl", "mapServiceUrl"}


def extract_arcgis_item_id(source_url: str) -> str | None:
    """Return the ArcGIS application item id from a supported app URL."""
    parsed = urlparse(source_url)
    query = parsed.query
    for pair in query.split("&"):
        key, _, value = pair.partition("=")
        if key.lower() == "appid" and _ARCGIS_ITEM_ID.fullmatch(value):
            return value
    return None


def discover_arcgis_references(metadata: Any) -> list[dict[str, Any]]:
    """Extract explicit ArcGIS item/service references from already-retrieved metadata.

    This function does not fetch remote resources and does not infer service URLs.
    Only explicit IDs/URLs present in the supplied metadata are returned.
    """
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, path: str) -> None:
        value = value.strip()
        if not value:
            return
        key = (kind, value)
        if key in seen:
            return
        seen.add(key)
        found.append({"kind": kind, "value": value, "path": path})

    def walk(value: Any, path: str = "root") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if isinstance(child, str):
                    if key in _SERVICE_URL_KEYS and "/rest/services/" in child:
                        add("service_url", child, child_path)
                    elif key.lower() in {"webmap", "webmapid", "webmapitemid", "itemid"} and _ARCGIS_ITEM_ID.fullmatch(child):
                        add("item_id", child, child_path)
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            for match in re.findall(r"(?i)(?:https?://[^\s\"']+/rest/services/[^\s\"']+)", value):
                add("service_url", match.rstrip(",.;)"), path)

    walk(metadata)
    return found
