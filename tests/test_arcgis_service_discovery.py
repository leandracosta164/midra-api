from app.services.arcgis_service_discovery import (
    discover_arcgis_references,
    extract_arcgis_item_id,
)


def test_extracts_arcgis_app_item_id():
    assert extract_arcgis_item_id(
        "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c"
    ) == "09bd902a48ef45348d2d59283c89673c"


def test_rejects_malformed_app_id():
    assert extract_arcgis_item_id("https://example.com/?appid=not-an-item") is None


def test_extracts_explicit_webmap_and_service_references():
    data = {
        "webmap": "0123456789abcdef0123456789abcdef",
        "layers": [
            {"url": "https://example.gov/arcgis/rest/services/Zoning/FeatureServer/0"},
            {"featureServiceUrl": "https://example.gov/arcgis/rest/services/Parcels/FeatureServer"},
        ],
    }
    result = discover_arcgis_references(data)
    assert [(x["kind"], x["value"]) for x in result] == [
        ("item_id", "0123456789abcdef0123456789abcdef"),
        ("service_url", "https://example.gov/arcgis/rest/services/Zoning/FeatureServer/0"),
        ("service_url", "https://example.gov/arcgis/rest/services/Parcels/FeatureServer"),
    ]


def test_does_not_infer_service_from_item_id():
    result = discover_arcgis_references({"webmap": "0123456789abcdef0123456789abcdef"})
    assert result == [
        {"kind": "item_id", "value": "0123456789abcdef0123456789abcdef", "path": "root.webmap"}
    ]
