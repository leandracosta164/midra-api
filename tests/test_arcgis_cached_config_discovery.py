
from app.services.arcgis_cached_config_discovery import discover_arcgis_cached_references

def test_discovers_explicit_web_map_and_feature_service():
    payload = b'{"webMap":"0123456789abcdef0123456789abcdef","url":"https://x.example/FeatureServer/0"}'
    r = discover_arcgis_cached_references(payload)
    assert r["status"] == "REFERENCES_DISCOVERED"
    assert r["web_map_ids"] == ["0123456789abcdef0123456789abcdef"]
    assert r["service_urls"] == ["https://x.example/FeatureServer/0"]

def test_does_not_invent_references():
    r = discover_arcgis_cached_references(b"<html><body>zoning map</body></html>")
    assert r["status"] == "NO_REFERENCES_FOUND"
    assert r["item_ids"] == []
    assert r["service_urls"] == []

def test_extracts_explicit_arcgis_item_ids():
    r = discover_arcgis_cached_references(b'"itemId":"ABCDEFABCDEFABCDEFABCDEFABCDEFAB"')
    assert "abcdefabcdefabcdefabcdefabcdefab" in r["item_ids"]
