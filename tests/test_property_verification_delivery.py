from app.services.property_delivery_orchestration import build_property_delivery_bundle
from app.services.property_report_manifest import build_report_manifest
from app.services.property_verification_delivery import build_delivery_verification_summary


def _analysis():
    return {
        "verification_items": [
            "VERIFY WETLANDS: confirm mapping",
            {"code": "STRUCTURED_REVIEW", "status": "VERIFY"},
            "VERIFY ZONING CANDIDATE: confirm authority",
        ],
        "environmental_verification_items": ["VERIFY WETLANDS: confirm mapping"],
        "zoning_candidate_verification_items": ["VERIFY ZONING CANDIDATE: confirm authority"],
    }


def test_adapter_preserves_durable_verification_items_without_reinterpretation():
    summary = build_delivery_verification_summary(_analysis())
    assert summary["status"] == "VERIFICATION_REQUIRED"
    assert summary["items"][1] == {"code": "STRUCTURED_REVIEW", "status": "VERIFY"}
    assert summary["environmental_items"] == ["VERIFY WETLANDS: confirm mapping"]
    assert summary["zoning_candidate_items"] == ["VERIFY ZONING CANDIDATE: confirm authority"]
    assert summary["professional_boundary"]["engineer_reviewed"] is False
    assert summary["professional_boundary"]["engineer_accepted"] is False


def test_bundle_carries_verification_summary_separately_from_artifacts():
    summary = build_delivery_verification_summary(_analysis())
    bundle = build_property_delivery_bundle(
        analysis_id="analysis-verify",
        property_record={"municipality": "Example City", "block": "1", "lot": "2"},
        project_goal="pool",
        sources=[],
        verification_summary=summary,
        report_profile="preliminary",
    )
    assert bundle["master_evidence_package"]["verification_summary"] == summary
    assert bundle["workspace"]["verification_summary"] == summary
    assert bundle["master_evidence_package"]["artifacts"] == []
    assert bundle["customer_report"]["sections"]["verification_summary"] is True


def test_report_manifest_does_not_invent_verification_summary_when_absent():
    report = build_report_manifest(report_profile="complete", evidence_package={"artifacts": []})
    assert report["sections"]["verification_summary"] is False
