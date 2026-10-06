from app.services.property_evidence_artifacts import build_property_evidence_package
from app.services.property_report_manifest import build_report_manifest


def _sources():
    return [
        {"label": "Official Zoning Map", "source_url": "https://example.gov/zoning-map.pdf", "source_role": "zoning_map", "municipal_official_link_verified": True, "content_hash": "abc"},
        {"label": "Tax Map Sheet 12", "source_url": "https://example.gov/taxmaps/sheet12.pdf", "source_role": "tax_map", "municipal_official_link_verified": True, "tax_map_sheet": "12", "content_hash": "def"},
    ]


def test_evidence_package_preserves_zoning_and_tax_maps_as_independent_artifacts():
    package = build_property_evidence_package(municipality="Example Borough", block="55", lot="14", sources=_sources())
    assert [a["artifact_type"] for a in package["artifacts"]] == ["ZONING_MAP", "TAX_MAP"]
    assert package["artifacts"][1]["tax_map_sheet"] == "12"


def test_preliminary_report_contains_integrated_midra_map_not_zoning_or_tax_exhibits():
    package = build_property_evidence_package(municipality="Example Borough", block="55", lot="14", sources=_sources())
    report = build_report_manifest(report_profile="preliminary", evidence_package=package)
    assert report["sections"]["midra_property_map"] is True
    assert report["sections"]["zoning_map_exhibit"] is False
    assert report["sections"]["tax_map_exhibit"] is False
    assert report["artifact_ids"] == []


def test_complete_report_includes_verified_zoning_and_tax_map_artifacts():
    package = build_property_evidence_package(municipality="Example Borough", block="55", lot="14", sources=_sources())
    report = build_report_manifest(report_profile="complete", evidence_package=package)
    assert report["sections"]["midra_property_map"] is True
    assert report["sections"]["zoning_map_exhibit"] is True
    assert report["sections"]["tax_map_exhibit"] is True
    assert len(report["artifact_ids"]) == 2


def test_unverified_map_can_be_preserved_but_not_rendered_as_complete_report_evidence():
    package = build_property_evidence_package(municipality="Example Borough", block="1", lot="2", sources=[{"label":"Tax Map", "source_url":"https://unknown.example/taxmap.pdf", "source_role":"tax_map"}])
    assert len(package["artifacts"]) == 1
    assert package["artifacts"][0]["workspace"]["download_original"] is True
    assert package["artifacts"][0]["report_eligibility"]["complete"] is False
    assert build_report_manifest(report_profile="complete", evidence_package=package)["artifact_ids"] == []
