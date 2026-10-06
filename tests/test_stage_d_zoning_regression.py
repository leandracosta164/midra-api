from app.services.zoning_evidence import resolve_zoning_evidence


def test_howell_twp_hd4():
    r = resolve_zoning_evidence(
        municipality="HOWELL TWP",
        parcel={"block": "177", "lot": "16.01"},
    )
    assert r["status"] == "ZONING_RESOLVED"
    assert r["zoning_district"] == "HD-4"
    assert r["authoritative"] is True


def test_howell_township_alias():
    r = resolve_zoning_evidence(
        municipality="HOWELL TOWNSHIP",
        parcel={"block": "177", "lot": "16.01"},
    )
    assert r["status"] == "ZONING_RESOLVED"
    assert r["zoning_district"] == "HD-4"
    assert r["authoritative"] is True


def test_marlboro_twp_cf():
    r = resolve_zoning_evidence(
        municipality="MARLBORO TWP",
        parcel={"block": "177", "lot": "16"},
    )
    assert r["status"] == "ZONING_RESOLVED"
    assert r["zoning_district"] == "CF"
    assert r["authoritative"] is True


def test_marlboro_township_alias():
    r = resolve_zoning_evidence(
        municipality="MARLBORO TOWNSHIP",
        parcel={"block": "177", "lot": "16"},
    )
    assert r["status"] == "ZONING_RESOLVED"
    assert r["zoning_district"] == "CF"
    assert r["authoritative"] is True


def test_unknown_parcel_remains_verify():
    r = resolve_zoning_evidence(
        municipality="HOWELL TWP",
        parcel={"block": "999", "lot": "999"},
    )
    assert r["status"] == "ZONING_NOT_RESOLVED"
    assert r["zoning_district"] == "VERIFY"
    assert r["authoritative"] is False


def test_cross_municipality_evidence_is_rejected():
    r = resolve_zoning_evidence(
        municipality="HOWELL TWP",
        parcel={"block": "253", "lot": "37.01"},
        zoning_resolution={
            "status": "ZONING_RESOLVED",
            "zoning_district": "CF",
            "confidence": "OFFICIAL_PARCEL_SPECIFIC",
            "source": {
                "municipality": "Marlboro Township",
                "authoritative": True,
            },
            "parcel_reference": {
                "block": "253",
                "lot": "37.01",
            },
        },
    )
    assert r["status"] == "ZONING_NOT_RESOLVED"
    assert r["zoning_district"] == "VERIFY"
    assert r["authoritative"] is False
