from app.services.zoning_evidence_adapter import adapt_parcel_zoning_evidence


def _evidence(**source_overrides):
    source = {
        "source_type": "municipal_zoning_gis",
        "url": "https://example.nj.us/zoning/map",
        "description": "Municipal parcel-specific zoning source",
        "authoritative": True,
    }
    source.update(source_overrides)
    return {
        "municipality": "Perth Amboy City",
        "block": "10",
        "lot": "2.01",
        "zoning_district": "R-25",
        "evidence_type": "MUNICIPAL_ZONING_GIS",
        "source": source,
    }


def test_adapter_resolves_matching_authoritative_parcel_evidence():
    result = adapt_parcel_zoning_evidence(
        municipality="Perth Amboy City",
        parcel={"block": "10", "lot": "2.01"},
        evidence=_evidence(),
    )
    assert result["status"] == "ZONING_RESOLVED"
    assert result["zoning_district"] == "R-25"
    assert result["authoritative"] is True


def test_adapter_rejects_cross_municipality_evidence():
    evidence = _evidence()
    evidence["municipality"] = "Marlboro Township"
    result = adapt_parcel_zoning_evidence(
        municipality="Perth Amboy City",
        parcel={"block": "10", "lot": "2.01"},
        evidence=evidence,
    )
    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["zoning_district"] == "VERIFY"


def test_adapter_rejects_block_lot_mismatch():
    result = adapt_parcel_zoning_evidence(
        municipality="Perth Amboy City",
        parcel={"block": "10", "lot": "9"},
        evidence=_evidence(),
    )
    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["authoritative"] is False


def test_adapter_rejects_non_authoritative_candidate():
    result = adapt_parcel_zoning_evidence(
        municipality="Perth Amboy City",
        parcel={"block": "10", "lot": "2.01"},
        evidence=_evidence(authoritative=False),
    )
    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["zoning_district"] == "VERIFY"


def test_adapter_accepts_existing_municipality_aliases():
    evidence = _evidence()
    evidence["municipality"] = "Howell Township"
    result = adapt_parcel_zoning_evidence(
        municipality="HOWELL TWP",
        parcel={"block": "177", "lot": "16.01"},
        evidence={
            **evidence,
            "block": "177",
            "lot": "16.01",
            "zoning_district": "HD-4",
            "source": {**evidence["source"], "municipality": "Howell Township"},
        },
    )
    assert result["status"] == "ZONING_RESOLVED"
    assert result["zoning_district"] == "HD-4"
