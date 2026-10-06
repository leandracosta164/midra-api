from app.services.property_report_manifest import build_report_manifest
from app.services.property_verification_delivery import build_delivery_verification_summary


def test_category_only_environmental_context_is_still_verification_required():
    summary = build_delivery_verification_summary({
        "verification_items": [],
        "environmental_verification_items": ["VERIFY FLOOD: confirm mapping"],
        "zoning_candidate_verification_items": [],
    })
    assert summary["status"] == "VERIFICATION_REQUIRED"
    report = build_report_manifest(
        report_profile="preliminary",
        evidence_package={"artifacts": [], "verification_summary": summary},
    )
    assert report["verification_context"]["requires_verification"] is True
    assert report["verification_context"]["item_count"] == 0
    assert report["verification_context"]["environmental_item_count"] == 1


def test_category_only_zoning_context_is_still_verification_required():
    summary = build_delivery_verification_summary({
        "verification_items": [],
        "environmental_verification_items": [],
        "zoning_candidate_verification_items": ["VERIFY ZONING CANDIDATE: confirm authority"],
    })
    assert summary["status"] == "VERIFICATION_REQUIRED"
    report = build_report_manifest(
        report_profile="complete",
        evidence_package={"artifacts": [], "verification_summary": summary},
    )
    assert report["verification_context"]["requires_verification"] is True
    assert report["verification_context"]["zoning_candidate_item_count"] == 1


def test_empty_context_remains_absent():
    assert build_delivery_verification_summary({
        "verification_items": [],
        "environmental_verification_items": [],
        "zoning_candidate_verification_items": [],
    }) == {}
