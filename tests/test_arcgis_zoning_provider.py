import json

from app.services.arcgis_zoning_provider import ArcGISZoningMapProvider


SOURCE = {
    "municipality": "Example Township",
    "source_role": "zoning_map",
    "source_url": "https://example.maps.arcgis.com/apps/instant/basic/index.html?appid=123",
    "authoritative": False,
}


def _content(features):
    return json.dumps({"features": features}).encode("utf-8")


def test_extracts_matching_parcel_district():
    provider = ArcGISZoningMapProvider()
    record = provider.extract(
        municipality="Example Township",
        block="10",
        lot="2",
        source=SOURCE,
        content=_content([
            {"attributes": {"BLOCK": "10", "LOT": "2", "ZONE": "R-10"}},
        ]),
    )
    assert record is not None
    assert record.zoning_district == "R-10"
    assert record.evidence_type == "ARCGIS_PARCEL_FEATURE"
    assert record.source["authoritative"] is False


def test_rejects_non_arcgis_or_non_map_sources():
    provider = ArcGISZoningMapProvider()
    assert provider.supports({**SOURCE, "source_role": "zoning_ordinance"}) is False
    assert provider.supports({**SOURCE, "source_url": "https://example.gov/zoning"}) is False


def test_rejects_html_or_non_feature_json():
    provider = ArcGISZoningMapProvider()
    assert provider.extract(
        municipality="Example Township",
        block="10",
        lot="2",
        source=SOURCE,
        content=b"<html></html>",
    ) is None
    assert provider.extract(
        municipality="Example Township",
        block="10",
        lot="2",
        source=SOURCE,
        content=b'{"foo": "bar"}',
    ) is None


def test_rejects_ambiguous_duplicate_parcels():
    provider = ArcGISZoningMapProvider()
    content = _content([
        {"attributes": {"block": "10", "lot": "2", "district": "R-10"}},
        {"attributes": {"block": "10", "lot": "2", "district": "R-20"}},
    ])
    assert provider.extract(
        municipality="Example Township",
        block="10",
        lot="2",
        source=SOURCE,
        content=content,
    ) is None


def test_rejects_municipality_mismatch_when_present():
    provider = ArcGISZoningMapProvider()
    content = _content([
        {"attributes": {"block": "10", "lot": "2", "municipality": "Other Township", "zone": "R-10"}},
    ])
    assert provider.extract(
        municipality="Example Township",
        block="10",
        lot="2",
        source=SOURCE,
        content=content,
    ) is None
