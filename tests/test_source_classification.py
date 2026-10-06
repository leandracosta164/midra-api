from app.services.source_classification import classify_discovered_source


def test_classifies_ordinance_source_as_zoning_ordinance():
    result = classify_discovered_source("Zoning Ordinances", "https://www.example.nj.us/zoning/ordinance.pdf")
    assert result["source_role"] == "zoning_ordinance"
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False


def test_classifies_map_source_as_zoning_map():
    result = classify_discovered_source("Zoning Map Links", "https://example.maps.arcgis.com/apps/viewer")
    assert result["source_role"] == "zoning_map"
    assert result["evidence_status"] == "DISCOVERED_CANDIDATE"


def test_classification_does_not_promote_external_source():
    result = classify_discovered_source("Zoning Information", "https://example.com/zoning")
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False


def test_code_enforcement_department_is_not_misclassified_as_zoning_ordinance():
    result = classify_discovered_source(
        "Code Enforcement",
        "https://www.exampleboroughnj.org/government/departments/code_enforcement",
        {"municipality": "Example Borough"},
    )
    assert result["source_role"] != "zoning_ordinance"
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False


def test_municipal_code_remains_classified_as_zoning_ordinance_candidate():
    result = classify_discovered_source(
        "Municipal Code",
        "https://www.exampleboroughnj.org/government/municipal_code",
        {"municipality": "Example Borough"},
    )
    assert result["source_role"] == "zoning_ordinance"
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False
