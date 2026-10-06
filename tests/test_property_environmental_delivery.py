from app.api.property_records import _delivery_environmental_screening_from_analysis
from app.services.property_delivery_orchestration import build_property_delivery_bundle


def _screening():
    return {
        "status": "SCREENING_EVALUATED",
        "wetlands": {
            "status": "SCREENING_COMPLETE",
            "screening_result": "MAPPED_WETLANDS_INTERSECTION",
            "mapped_intersection": True,
            "regulatory_determination": False,
            "source": {"agency": "NJDEP", "dataset": "Wetlands (2012)", "url": "https://example.gov/wetlands"},
            "evidence": [{"object_id": 1}],
            "limitations": ["screening only"],
        },
        "flood": {
            "status": "SCREENING_COMPLETE",
            "screening_result": "NO_MAPPED_INTERSECTION_RETURNED",
            "mapped_intersection": False,
            "regulatory_determination": False,
            "actual_flood_risk_calculated": False,
            "source": {"agency": "FEMA / NJDEP", "dataset": "NFHL", "url": "https://example.gov/flood"},
            "evidence": [],
            "limitations": ["no hit does not establish no flood risk"],
        },
        "professional_boundary": {
            "wetlands": {"definitive": False},
            "flood": {"definitive": False},
        },
    }


def test_delivery_environmental_adapter_preserves_screening_without_promotion():
    result = _delivery_environmental_screening_from_analysis({"environmental_constraints": _screening()})
    assert result["status"] == "SCREENING_EVALUATED"
    assert result["wetlands"]["mapped_intersection"] is True
    assert result["wetlands"]["regulatory_determination"] is False
    assert result["flood"]["mapped_intersection"] is False
    assert result["flood"]["actual_flood_risk_calculated"] is False
    assert "no flood risk" in result["flood"]["limitations"][0]


def test_delivery_environmental_adapter_ignores_not_evaluated_state():
    assert _delivery_environmental_screening_from_analysis({
        "environmental_constraints": {"status": "NOT_EVALUATED", "wetlands": {"mapped_intersection": True}}
    }) == {}


def test_delivery_bundle_keeps_environmental_screening_separate_from_map_artifacts():
    screening = _delivery_environmental_screening_from_analysis({"environmental_constraints": _screening()})
    bundle = build_property_delivery_bundle(
        analysis_id="analysis-1",
        property_record={"municipality": "Howell", "block": "1", "lot": "2"},
        project_goal="subdivision",
        sources=[],
        environmental_screening=screening,
        report_profile="complete",
    )
    assert bundle["master_evidence_package"]["artifacts"] == []
    preserved = bundle["master_evidence_package"]["screening_evidence"]
    assert preserved["wetlands"]["screening_result"] == "MAPPED_WETLANDS_INTERSECTION"
    assert preserved["flood"]["screening_result"] == "NO_MAPPED_INTERSECTION_RETURNED"
    assert bundle["customer_report"]["sections"]["environmental_screening"] is True
    assert bundle["customer_report"]["sections"]["environmental_source_index"] is True
    assert bundle["workspace"]["environmental_screening"] == preserved


def test_preliminary_report_can_include_screening_without_expanding_source_index():
    screening = _delivery_environmental_screening_from_analysis({"environmental_constraints": _screening()})
    bundle = build_property_delivery_bundle(
        analysis_id="analysis-2",
        property_record={"municipality": "Howell"},
        project_goal="general research",
        sources=[],
        environmental_screening=screening,
        report_profile="preliminary",
    )
    assert bundle["customer_report"]["sections"]["environmental_screening"] is True
    assert bundle["customer_report"]["sections"]["environmental_source_index"] is False
