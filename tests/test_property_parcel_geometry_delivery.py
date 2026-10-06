from app.main import PropertyRequest, _build_property_information


def test_property_information_preserves_resolved_parcel_geometry_and_provenance():
    payload = PropertyRequest(address="123 Main Street, Example, NJ")
    geometry = {
        "rings": [[[-74.1, 40.5], [-74.09, 40.5], [-74.09, 40.51], [-74.1, 40.5]]],
        "spatialReference": {"wkid": 4326},
    }
    source = {
        "agency": "NJ Office of GIS",
        "dataset": "Parcels and MOD-IV Composite of New Jersey",
        "url": "https://maps.nj.gov/example",
    }
    match = {"status": "PARCEL_FOUND", "match_score": 88}

    result = _build_property_information(
        payload,
        {
            "matched_address": "123 Main Street",
            "municipality": "Example",
            "county": "Example County",
            "state": "New Jersey",
            "coordinates": {"longitude": -74.095, "latitude": 40.505},
            "parcel": {
                "block": "10",
                "lot": "2",
                "geometry": geometry,
            },
            "parcel_source": source,
            "parcel_match": match,
        },
    )

    assert result["parcel"]["geometry"] == geometry
    assert result["parcel_source"] == source
    assert result["parcel_match"] == match


def test_property_information_does_not_invent_parcel_source_or_match():
    payload = PropertyRequest(address="123 Main Street, Example, NJ")
    result = _build_property_information(
        payload,
        {
            "municipality": "Example",
            "coordinates": {"longitude": -74.095, "latitude": 40.505},
            "parcel": None,
        },
    )

    assert result["parcel"] is None
    assert result["parcel_source"] is None
    assert result["parcel_match"] is None
