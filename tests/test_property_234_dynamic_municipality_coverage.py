from app.services.municipality_coverage import build_municipality_coverage


def test_dynamic_source_identification_is_visible_without_promoting_zoning():
    result = build_municipality_coverage(
        municipality="Example Borough",
        zoning_intelligence={"zoning_district": "VERIFY", "bulk_requirements": [], "project_requirements": []},
        zoning_resolution={"zoning_district": "VERIFY", "confidence": "VERIFY"},
        project_goal="addition",
        municipality_source_registry={
            "status": "DCA_SOURCES_DISCOVERED",
            "registered": True,
            "municipality": "Example Borough",
            "sources": {"zoning": {"url": "https://example.invalid/zoning"}},
        },
    )
    assert result["status"] == "SOURCE_IDENTIFIED_VERIFY"
    assert result["municipality_registered"] is False
    assert result["municipality_source_identified"] is True
    assert result["municipality_source_status"] == "DCA_SOURCES_DISCOVERED"
    assert result["zoning_resolution_supported"] is False
    assert result["district_rules_supported"] is False
    assert result["project_rules_supported"] is False


def test_no_discovered_source_retains_unregistered_contract():
    result = build_municipality_coverage(
        municipality="Unknown Borough",
        zoning_intelligence={},
        zoning_resolution={},
        municipality_source_registry={"status": "DCA_SOURCE_INDEX_NOT_FOUND", "registered": False},
    )
    assert result["status"] == "UNREGISTERED"
    assert result["municipality_registered"] is False
    assert result["municipality_source_identified"] is False


def test_static_registered_municipality_retains_existing_status_contract():
    result = build_municipality_coverage(
        municipality="Howell Township",
        zoning_intelligence={"zoning_district": "VERIFY", "bulk_requirements": [], "project_requirements": []},
        zoning_resolution={"zoning_district": "VERIFY", "confidence": "VERIFY"},
        municipality_source_registry={"status": "OFFICIAL_SOURCES_IDENTIFIED", "registered": True},
    )
    assert result["status"] == "REGISTERED"
    assert result["municipality_registered"] is True
    assert result["municipality_source_identified"] is True
    assert result["zoning_resolution_supported"] is False
