from app.services.property_report_manifest import build_report_manifest


def _verification_summary():
    return {
        "status": "VERIFICATION_REQUIRED",
        "items": [
            "VERIFY WETLANDS: confirm mapping",
            {"code": "STRUCTURED_REVIEW", "status": "VERIFY"},
            "VERIFY ZONING CANDIDATE: confirm authority",
        ],
        "environmental_items": ["VERIFY WETLANDS: confirm mapping"],
        "zoning_candidate_items": ["VERIFY ZONING CANDIDATE: confirm authority"],
        "professional_boundary": {
            "engineer_reviewed": False,
            "engineer_accepted": False,
            "notice": "Verification items remain MIDRA Analysis context.",
        },
    }


def test_report_manifest_exposes_verification_context_counts_without_reinterpretation():
    report = build_report_manifest(
        report_profile="preliminary",
        evidence_package={"artifacts": [], "verification_summary": _verification_summary()},
    )
    context = report["verification_context"]
    assert report["sections"]["verification_summary"] is True
    assert context["status"] == "VERIFICATION_REQUIRED"
    assert context["item_count"] == 3
    assert context["environmental_item_count"] == 1
    assert context["zoning_candidate_item_count"] == 1
    assert context["requires_verification"] is True
    assert context["professional_boundary"]["engineer_reviewed"] is False
    assert context["professional_boundary"]["engineer_accepted"] is False


def test_report_manifest_omits_verification_context_when_no_summary_exists():
    report = build_report_manifest(
        report_profile="complete",
        evidence_package={"artifacts": []},
    )
    assert report["sections"]["verification_summary"] is False
    assert report["verification_context"] == {}


def test_category_only_verification_context_still_requires_verification():
    report = build_report_manifest(
        report_profile="preliminary",
        evidence_package={
            "artifacts": [],
            "verification_summary": {
                "status": "VERIFICATION_CONTEXT_AVAILABLE",
                "items": [],
                "environmental_items": ["VERIFY FLOOD: confirm mapping"],
                "zoning_candidate_items": [],
            },
        },
    )
    context = report["verification_context"]
    assert context["item_count"] == 0
    assert context["environmental_item_count"] == 1
    assert context["requires_verification"] is True
