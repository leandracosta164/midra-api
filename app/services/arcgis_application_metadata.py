"""Resolve public ArcGIS application metadata from an explicit application item ID."""
from __future__ import annotations

from typing import Any

import httpx

_ARCGIS_ITEM_BASE = "https://www.arcgis.com/sharing/rest/content/items"


def _validate_item_id(item_id: str) -> str:
    value = str(item_id).strip().lower()
    if len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Invalid ArcGIS item ID")
    return value


def build_arcgis_item_urls(item_id: str) -> dict[str, str]:
    """Build only documented ArcGIS item endpoints from an explicit item ID."""
    value = _validate_item_id(item_id)
    return {
        "item_url": f"{_ARCGIS_ITEM_BASE}/{value}?f=json",
        "data_url": f"{_ARCGIS_ITEM_BASE}/{value}/data?f=json",
    }


def retrieve_arcgis_application_metadata(
    item_id: str,
    *,
    timeout: float = 20.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Retrieve public ArcGIS item metadata and item data without inventing references."""
    urls = build_arcgis_item_urls(item_id)
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        item_response = http.get(urls["item_url"])
        item_response.raise_for_status()
        item = item_response.json()
        if not isinstance(item, dict) or item.get("error"):
            return {
                "status": "ARCGIS_ITEM_METADATA_FAILED",
                "item_id": _validate_item_id(item_id),
                "item_url": urls["item_url"],
                "data_url": urls["data_url"],
                "item": item if isinstance(item, dict) else {},
                "data": {},
            }

        data_response = http.get(urls["data_url"])
        data_response.raise_for_status()
        data = data_response.json()
        if not isinstance(data, dict):
            data = {}

        return {
            "status": "ARCGIS_METADATA_RETRIEVED",
            "item_id": _validate_item_id(item_id),
            "item_url": urls["item_url"],
            "data_url": urls["data_url"],
            "item": item,
            "data": data,
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {
            "status": "ARCGIS_METADATA_RETRIEVAL_FAILED",
            "item_id": _validate_item_id(item_id),
            "item_url": urls["item_url"],
            "data_url": urls["data_url"],
            "item": {},
            "data": {},
            "error": str(exc),
        }
    finally:
        if owns_client:
            http.close()
