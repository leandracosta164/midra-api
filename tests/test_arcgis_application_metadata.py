import httpx
import pytest

from app.services.arcgis_application_metadata import (
    build_arcgis_item_urls,
    retrieve_arcgis_application_metadata,
)

ITEM_ID = "0123456789abcdef0123456789abcdef"


def test_builds_documented_item_endpoints_only():
    urls = build_arcgis_item_urls(ITEM_ID.upper())
    assert urls["item_url"] == f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}?f=json"
    assert urls["data_url"] == f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}/data?f=json"


def test_rejects_invalid_item_id():
    with pytest.raises(ValueError):
        build_arcgis_item_urls("not-an-item-id")


def test_retrieves_item_and_data_without_inventing_service_url():
    seen = []

    def handler(request: httpx.Request):
        seen.append(str(request.url))
        if request.url.path.endswith("/data"):
            return httpx.Response(200, json={"webMap": ITEM_ID})
        return httpx.Response(200, json={"id": ITEM_ID, "type": "Web Mapping Application"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = retrieve_arcgis_application_metadata(ITEM_ID, client=client)

    assert result["status"] == "ARCGIS_METADATA_RETRIEVED"
    assert result["item"]["id"] == ITEM_ID
    assert result["data"]["webMap"] == ITEM_ID
    assert all("FeatureServer" not in url and "MapServer" not in url for url in seen)
    assert len(seen) == 2


def test_handles_public_metadata_error():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"error": {"message": "Item not found"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = retrieve_arcgis_application_metadata(ITEM_ID, client=client)

    assert result["status"] == "ARCGIS_ITEM_METADATA_FAILED"
    assert result["data"] == {}
