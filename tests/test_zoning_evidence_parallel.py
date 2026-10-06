from app.services.zoning_evidence_parallel import (
    attach_dynamic_evidence_candidate,
    dynamic_candidate_is_promotable,
)


def test_dynamic_candidate_is_attached_without_changing_legacy_contract():
    legacy = {
        "status": "ZONING_RESOLVED",
        "zoning_district": "HD-4",
        "rules_registry": {"project_rules_available": True},
    }
    dynamic = {"status": "ZONING_NOT_RESOLVED", "reason": "VERIFY"}

    result = attach_dynamic_evidence_candidate(legacy, dynamic)

    assert result["status"] == legacy["status"]
    assert result["zoning_district"] == "HD-4"
    assert result["rules_registry"] == legacy["rules_registry"]
    assert result["dynamic_evidence_candidate"] == dynamic
    assert "dynamic_evidence_candidate" not in legacy


def test_authoritative_dynamic_result_is_promotable():
    result = {
        "status": "ZONING_RESOLVED",
        "record": {
            "zoning_district": "R-20",
            "source": {"authoritative": True},
        },
    }
    assert dynamic_candidate_is_promotable(result) is True


def test_non_authoritative_or_unresolved_dynamic_result_is_not_promotable():
    assert dynamic_candidate_is_promotable({"status": "ZONING_NOT_RESOLVED"}) is False
    assert dynamic_candidate_is_promotable({
        "status": "ZONING_RESOLVED",
        "record": {"zoning_district": "R-20", "source": {"authoritative": False}},
    }) is False
