from app.services.zoning_evidence_provider import ZoningEvidenceRecord


def test_record_maps_to_generic_adapter_contract():
    record = ZoningEvidenceRecord(
        municipality="Perth Amboy City",
        block="10",
        lot="2",
        zoning_district="R-10",
        source={"source_type": "municipal_gis", "authoritative": True},
    )
    assert record.as_adapter_input() == {
        "municipality": "Perth Amboy City",
        "block": "10",
        "lot": "2",
        "zoning_district": "R-10",
        "evidence_type": "PARCEL_SPECIFIC_SOURCE",
        "source": {"source_type": "municipal_gis", "authoritative": True},
    }
