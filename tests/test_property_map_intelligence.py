from app.services.property_map_intelligence import (
    resolve_property_maps,
    resolve_tax_map,
    resolve_zoning_map,
)


def test_zoning_map_prefers_verified_explicit_map_and_preserves_district():
    sources = [
        {
            "label": "Zoning Information",
            "source_url": "https://example.gov/zoning",
            "source_role": "zoning_administration",
        },
        {
            "label": "Official Zoning Map",
            "source_url": "https://example.gov/maps/zoning",
            "source_role": "zoning_map",
            "municipal_official_link_verified": True,
        },
    ]
    zoning = {
        "candidate": {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {"zoning_district": "R-60", "evidence": "ARCGIS_SPATIAL_INTERSECTION"},
        }
    }
    result = resolve_zoning_map(
        municipality="Example Borough",
        sources=sources,
        zoning_result=zoning,
    )
    assert result["status"] == "RESOLVED"
    assert result["source_url"] == "https://example.gov/maps/zoning"
    assert result["zoning_district"] == "R-60"
    assert result["parcel_intersection_verified"] is True


def test_tax_map_returns_explicit_sheet_without_guessing():
    result = resolve_tax_map(
        municipality="Example Borough",
        block="55",
        lot="14",
        sources=[{
            "label": "Tax Map Sheet 12",
            "source_url": "https://example.gov/taxmaps/sheet12.pdf",
            "source_role": "tax_map",
            "municipal_official_link_verified": True,
            "block": "55",
            "lot": "14",
            "tax_map_sheet": "12",
        }],
    )
    assert result["status"] == "RESOLVED"
    assert result["tax_map_sheet"] == "12"
    assert result["sheet_status"] == "RESOLVED"


def test_tax_map_does_not_infer_sheet_from_block_number():
    result = resolve_tax_map(
        municipality="Example Borough",
        block="55",
        lot="14",
        sources=[{
            "label": "Municipal Tax Maps",
            "source_url": "https://example.gov/taxmaps",
            "source_role": "tax_map",
            "municipal_official_link_verified": True,
        }],
    )
    assert result["status"] == "RESOLVED"
    assert result["tax_map_sheet"] is None
    assert result["sheet_status"] == "VERIFY"


def test_property_maps_keep_zoning_and_tax_evidence_independent():
    result = resolve_property_maps(
        municipality="Example Borough",
        block="1",
        lot="2",
        sources=[{
            "label": "Zoning Map",
            "source_url": "https://example.gov/zoning-map",
            "source_role": "zoning_map",
            "municipal_official_link_verified": True,
        }],
        zoning_result=None,
    )
    assert result["zoning_map"]["status"] == "RESOLVED"
    assert result["tax_map"]["status"] == "VERIFY"
    assert result["status"] == "PROPERTY_MAP_ANALYSIS_COMPLETE"

def test_zoning_map_role_does_not_leak_into_tax_map_classification():
    result = resolve_tax_map(
        municipality="Example Borough",
        block="1",
        lot="2",
        sources=[{
            "label": "Zoning Map",
            "source_url": "https://example.gov/zoning-map",
            "source_role": "zoning_map",
            "municipal_official_link_verified": True,
        }],
    )
    assert result["status"] == "VERIFY"
    assert result["reason"] == "NO_EXPLICIT_TAX_MAP_SOURCE"
