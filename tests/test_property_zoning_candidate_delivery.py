from app.services.property_delivery_orchestration import build_property_delivery_bundle
from app.services.property_report_manifest import build_report_manifest

CANDIDATE = {
    "status": "CANDIDATE_GEOMETRY_AVAILABLE",
    "candidate_only": True,
    "reason": None,
    "professional_boundary": {"definitive": False, "message": "Candidate geometry only."},
    "candidate": {
        "status": "ZONING_CANDIDATE_RESOLVED",
        "record": {
            "municipality": "Example City",
            "block": "10",
            "lot": "2",
            "zoning_district": "R-60",
            "evidence_type": "ARCGIS_SPATIAL_INTERSECTION",
            "mapped_geometries": [{"rings": [[[-74.3, 40.2], [-74.2, 40.2], [-74.3, 40.2]]]}],
            "geometry_role": "ZONING_CANDIDATE_GIS_GEOMETRY",
            "geometry_definitive": False,
            "source": {"source_url": "https://example.gov/zoning", "authoritative": False, "legal_control_confirmed": False},
        },
    },
}

def test_delivery_bundle_preserves_candidate_evidence_separately_from_map_artifacts():
    bundle = build_property_delivery_bundle(
        analysis_id="analysis-1",
        property_record={"municipality": "Example City", "block": "10", "lot": "2"},
        project_goal="pool",
        sources=[],
        zoning_candidate_evidence=CANDIDATE,
        report_profile="complete",
    )
    assert bundle["master_evidence_package"]["zoning_candidate_evidence"]["candidate_only"] is True
    assert bundle["workspace"]["zoning_candidate_evidence"]["candidate_only"] is True
    assert bundle["master_evidence_package"].get("artifacts") == []
    assert bundle["customer_report"]["sections"]["zoning_candidate_geometry"] is True
    assert bundle["customer_report"]["sections"]["zoning_candidate_source_index"] is True

def test_preliminary_report_keeps_candidate_evidence_but_not_complete_source_index():
    report = build_report_manifest(
        report_profile="preliminary",
        evidence_package={"zoning_candidate_evidence": CANDIDATE},
    )
    assert report["sections"]["zoning_candidate_geometry"] is True
    assert report["sections"]["zoning_candidate_source_index"] is False
