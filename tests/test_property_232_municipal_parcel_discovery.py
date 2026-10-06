from app.services import address_intelligence as ai


def _parcel_feature(object_id=77, municipality="Howell Township", block="145", lot="22"):
    return {
        "attributes": {
            "OBJECTID": object_id,
            "PCLBLOCK": block,
            "PCLLOT": lot,
            "MUN_NAME": municipality,
            "COUNTY": "Monmouth",
            "ST_ADDRESS": "1 TEST ROAD",
            "PROP_LOC": "1 TEST ROAD",
        },
        "geometry": {
            "rings": [[[-74.2, 40.1], [-74.19, 40.1], [-74.19, 40.11], [-74.2, 40.11], [-74.2, 40.1]]]
        },
        "centroid": {"x": -74.195, "y": 40.105},
    }


def test_parse_municipal_block_discovery_queries():
    assert ai.parse_new_jersey_parcel_search_query("Howell Block 145") == {
        "municipality": "Howell",
        "block": "145",
        "search_mode": "MUNICIPAL_BLOCK_DISCOVERY",
    }
    assert ai.parse_new_jersey_parcel_search_query("Howell 145/22") == {
        "municipality": "Howell",
        "block": "145",
        "lot": "22",
        "search_mode": "EXACT_BLOCK_LOT",
    }
    assert ai.parse_new_jersey_parcel_search_query("Block 145") is None


def test_municipal_block_discovery_is_bounded(monkeypatch):
    captured = {}

    def fake_request(url, params):
        captured.update(params)
        return {
            "features": [
                _parcel_feature(77, "Howell Township", "145", "22"),
                _parcel_feature(78, "Howell Township", "145", "23"),
            ]
        }, None

    monkeypatch.setattr(ai, "_request_json", fake_request)
    payload = ai.suggest_new_jersey_parcels("Howell Block 145")
    assert payload["parsed"]["search_mode"] == "MUNICIPAL_BLOCK_DISCOVERY"
    assert [row["lot"] for row in payload["suggestions"]] == ["22", "23"]
    assert "PCLBLOCK = '145'" in captured["where"]
    assert "UPPER(MUN_NAME) LIKE '%HOWELL%'" in captured["where"]
    assert captured["resultRecordCount"] == 250


def test_municipality_words_are_compared_without_form_suffixes(monkeypatch):
    monkeypatch.setattr(
        ai,
        "_query_parcels_by_municipal_block",
        lambda **kwargs: {
            "status": "PARCELS_FOUND",
            "features": [
                _parcel_feature(77, "Howell Township", "145", "22"),
                _parcel_feature(88, "Marlboro Township", "145", "1"),
            ],
            "notes": [],
        },
    )
    payload = ai.suggest_new_jersey_parcels("Township of Howell Block 145")
    assert [row["object_id"] for row in payload["suggestions"]] == [77]
