from app.services.dynamic_project_applicability import (
    build_dynamic_project_rule_candidate,
    evaluate_dynamic_project_applicability,
)


def _candidate(**source_overrides):
    source = {
        "source_url": "https://example.test/zoning-code",
        "authoritative": False,
        "legal_control_confirmed": False,
    }
    source.update(source_overrides)
    return build_dynamic_project_rule_candidate(
        municipality="Perth Amboy City",
        zoning_district="R-60",
        project_goal="pool",
        requirements=[{"requirement": "Pool requirement"}],
        source=source,
    )


def test_dynamic_rule_source_is_candidate_only_when_discovered():
    result = _candidate()
    assert result["status"] == "PROJECT_RULES_CANDIDATE"
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False


def test_dynamic_rule_candidate_cannot_be_promoted_without_authority():
    result = evaluate_dynamic_project_applicability(_candidate())
    assert result["status"] == "VERIFY"
    assert result["promotable"] is False
    assert result["reason"] == "SOURCE_AUTHORITY_NOT_CONFIRMED"


def test_dynamic_rule_candidate_requires_legal_control_even_when_authoritative():
    result = evaluate_dynamic_project_applicability(
        _candidate(authoritative=True, legal_control_confirmed=False)
    )
    assert result["status"] == "VERIFY"
    assert result["promotable"] is False
    assert result["reason"] == "LEGAL_CONTROL_NOT_CONFIRMED"


def test_dynamic_rule_candidate_can_reach_existing_applicability_evaluator_when_controlled():
    result = evaluate_dynamic_project_applicability(
        _candidate(authoritative=True, legal_control_confirmed=True)
    )
    assert result["promotable"] is True
    assert result["status"] == "VERIFY"
    assert result["evaluation"]["evaluated_requirement_count"] == 1
