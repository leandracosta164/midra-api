from app.services.dynamic_approval_pathway import evaluate_dynamic_approval_pathway


def test_missing_candidate_requires_verify():
    result = evaluate_dynamic_approval_pathway(None)
    assert result["status"] == "VERIFY"
    assert result["promotable"] is False


def test_unconfirmed_dynamic_pathway_cannot_be_promoted():
    result = evaluate_dynamic_approval_pathway({
        "primary_pathway": "SITE_PLAN_APPROVAL",
        "requirements": [{"requirement": "Site plan review"}],
        "authoritative": False,
        "legal_control_confirmed": False,
    })
    assert result["status"] == "VERIFY"
    assert result["promotable"] is False


def test_authoritative_legally_confirmed_pathway_is_available():
    result = evaluate_dynamic_approval_pathway({
        "primary_pathway": "SITE_PLAN_APPROVAL",
        "possible_alternative": "CONDITIONALLY_EXEMPT_SITE_PLAN",
        "reviewing_bodies": ["PLANNING_BOARD"],
        "requirements": [{"requirement": "Site plan review"}],
        "authoritative": True,
        "legal_control_confirmed": True,
        "source": {"source_url": "https://example.gov/zoning"},
    })
    assert result["status"] == "AVAILABLE"
    assert result["promotable"] is True
    assert result["primary_pathway"] == "SITE_PLAN_APPROVAL"
    assert result["reviewing_bodies"] == ["PLANNING_BOARD"]


def test_missing_explicit_primary_pathway_requires_verify_even_when_source_is_authoritative():
    result = evaluate_dynamic_approval_pathway({
        "requirements": [{"requirement": "Review"}],
        "authoritative": True,
        "legal_control_confirmed": True,
    })
    assert result["status"] == "VERIFY"
    assert result["promotable"] is False
