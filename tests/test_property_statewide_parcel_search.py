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
        "geometry": {"rings": [[[-74.2,40.1],[-74.19,40.1],[-74.19,40.11],[-74.2,40.11],[-74.2,40.1]]]},
        "centroid": {"x": -74.195, "y": 40.105},
    }

def test_parse_statewide_parcel_queries():
    assert ai.parse_new_jersey_parcel_query("Howell Block 145 Lot 22") == {
        "municipality": "Howell",
        "block": "145",
        "lot": "22",
    }
    assert ai.parse_new_jersey_parcel_query("145/22") == {"block": "145", "lot": "22"}
    assert ai.parse_new_jersey_parcel_query("123 Main Street") is None

def test_parcel_suggestions_filter_municipality(monkeypatch):
    monkeypatch.setattr(
        ai,
        "_query_parcels_by_block_lot",
        lambda **kwargs: {
            "status": "PARCELS_FOUND",
            "features": [
                _parcel_feature(77, "Howell Township"),
                _parcel_feature(88, "Marlboro Township"),
            ],
            "notes": [],
        },
    )
    payload=ai.suggest_new_jersey_parcels("Howell Block 145 Lot 22")
    assert payload["status"] == "PARCELS_FOUND"
    assert len(payload["suggestions"]) == 1
    item=payload["suggestions"][0]
    assert item["object_id"] == 77
    assert item["block"] == "145"
    assert item["lot"] == "22"
    assert item["source"]["authoritative"] is True

def test_direct_parcel_resolution_uses_exact_object_id(monkeypatch):
    def fake_request(url, params):
        assert params["where"] == "OBJECTID = 77"
        return {"features": [_parcel_feature()]}, None
    monkeypatch.setattr(ai, "_request_json", fake_request)
    result=ai.resolve_new_jersey_parcel_object_id(77, requested_label="Howell Block 145 Lot 22")
    assert result["status"] == "PROPERTY_RESOLVED"
    assert result["parcel"]["object_id"] == 77
    assert result["municipality"] == "Howell Township"
    assert result["coordinates"] == {"longitude": -74.195, "latitude": 40.105}
    assert result["parcel_match"]["status"] == "PARCEL_OBJECT_ID_RESOLVED"
    assert result["geocoding"]["status"] == "NOT_USED_PARCEL_IDENTITY"
