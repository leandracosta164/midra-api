from app.services.dynamic_property_analysis import analyze_dynamic_property


def _zoning_result(*, promotable=False):
    return {
        "status": "ZONING_RESOLVED" if promotable else "VERIFY",
        "candidate": {"status": "ZONING_CANDIDATE_RESOLVED", "record": {"zoning_district": "R-M(M)"}},
        "promotion": {"status": "ZONING_RESOLVED" if promotable else "VERIFY", "promotable": promotable},
    }


def test_dynamic_property_analysis_discovers_project_rule_before_zoning_promotion():
    captured = {}

    def discover(**kwargs):
        captured.update(kwargs)
        return {
            "status": "PROJECT_RULE_EVIDENCE_DISCOVERED",
            "requirements": [{"requirement": "pool rule"}],
            "source": {"authoritative": False, "legal_control_confirmed": False},
        }

    def evaluate(candidate):
        raise AssertionError("Project applicability must remain blocked by zoning promotion")

    result = analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="14",
        geometry={"rings": []},
        project_goal="pool",
        db=object(),
        zoning_analysis=lambda **_: _zoning_result(promotable=False),
        project_rule_discoverer=discover,
        project_evaluator=evaluate,
    )

    assert captured["zoning_district"] == "R-M(M)"
    assert captured["project_goal"] == "pool"
    assert result["project_applicability"]["reason"] == "DYNAMIC_ZONING_NOT_PROMOTABLE"


def test_dynamic_property_analysis_evaluates_supplied_candidates_after_zoning_promotion():
    project_candidate = {
        "status": "PROJECT_RULES_CANDIDATE",
        "municipality": "Perth Amboy City",
        "zoning_district": "R-60",
        "project_goal": "pool",
        "requirements": [{"requirement": "Pool review", "registry_applicability": "applicable"}],
        "authoritative": True,
        "legal_control_confirmed": True,
        "source": {"source_url": "https://example.gov/zoning", "authoritative": True},
    }
    approval_candidate = {
        "primary_pathway": "SITE_PLAN_APPROVAL",
        "requirements": [{"requirement": "Site plan review"}],
        "reviewing_bodies": ["PLANNING_BOARD"],
        "authoritative": True,
        "legal_control_confirmed": True,
    }

    result = analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        project_goal="Build a Pool",
        db=object(),
        zoning_analysis=lambda **_: _zoning_result(promotable=True),
        project_rule_candidate=project_candidate,
        approval_pathway_candidate=approval_candidate,
    )

    assert result["dynamic_promotable"] is True
    assert result["project_applicability"]["promotable"] is True
    assert result["approval_pathway"]["status"] == "AVAILABLE"
