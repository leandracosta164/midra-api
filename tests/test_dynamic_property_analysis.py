from app.services.dynamic_property_analysis import analyze_dynamic_property


def _zoning_result(*, promotable=False):
    return {
        "status": "ZONING_RESOLVED" if promotable else "VERIFY",
        "candidate": {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "municipality": "Perth Amboy City",
                "block": "55",
                "lot": "1",
                "zoning_district": "R-60",
                "source": {"authoritative": promotable, "legal_control_confirmed": promotable},
            },
        },
        "promotion": {"status": "ZONING_RESOLVED" if promotable else "VERIFY", "promotable": promotable},
    }


def test_dynamic_property_analysis_composes_zoning_and_blocks_downstream_when_not_promotable():
    result = analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        project_goal="Build a Pool",
        db=object(),
        zoning_analysis=lambda **_kwargs: _zoning_result(promotable=False),
    )

    assert result["status"] == "DYNAMIC_ANALYSIS_COMPLETE"
    assert result["dynamic_promotable"] is False
    assert result["project_applicability"]["reason"] == "DYNAMIC_ZONING_NOT_PROMOTABLE"
    assert result["approval_pathway"]["reason"] == "DYNAMIC_ZONING_NOT_PROMOTABLE"


def test_dynamic_property_analysis_accepts_controlled_zoning_and_evaluates_supplied_candidates():
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
        zoning_analysis=lambda **_kwargs: _zoning_result(promotable=True),
        project_rule_candidate=project_candidate,
        approval_pathway_candidate=approval_candidate,
    )

    assert result["dynamic_promotable"] is True
    assert result["project_applicability"]["promotable"] is True
    assert result["approval_pathway"]["status"] == "AVAILABLE"


def test_dynamic_property_analysis_never_invents_project_rules_when_none_are_available():
    result = analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        project_goal="Build a Pool",
        db=object(),
        zoning_analysis=lambda **_kwargs: _zoning_result(promotable=True),
    )

    assert result["project_applicability"]["status"] == "VERIFY"
    assert result["project_applicability"]["reason"] == "NO_PROJECT_RULE_EVIDENCE"
    assert result["approval_pathway"]["status"] == "VERIFY"


def test_dynamic_property_analysis_preserves_zoning_candidate_provenance():
    zoning = _zoning_result(promotable=False)
    zoning["candidate"]["record"]["evidence_type"] = "ARCGIS_SPATIAL_INTERSECTION"

    result = analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        project_goal="Build a Pool",
        db=object(),
        zoning_analysis=lambda **_kwargs: zoning,
    )

    assert result["zoning"]["candidate"]["record"]["evidence_type"] == "ARCGIS_SPATIAL_INTERSECTION"
    assert result["zoning"]["promotion"]["promotable"] is False


def test_dynamic_property_analysis_passes_requested_parcel_identity_to_zoning_layer():
    captured = {}

    def zoning_analysis(**kwargs):
        captured.update(kwargs)
        return _zoning_result(promotable=False)

    analyze_dynamic_property(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        project_goal="Build a Pool",
        db=object(),
        zoning_analysis=zoning_analysis,
    )

    assert captured["municipality"] == "Perth Amboy City"
    assert captured["block"] == "55"
    assert captured["lot"] == "1"
    assert captured["geometry"] == {"rings": []}


def test_dynamic_property_analysis_exposes_discovered_project_rule_candidate_without_promoting_it():
    class _Catalog:
        active = True
        municipality = "Perth Amboy City"
        label = "Municipal Code"
        source_url = "https://example.gov/code"
        source_role = "zoning_ordinance"
        authority_tier = "likely_municipal_or_state_domain"
        evidence_status = "DISCOVERED_CANDIDATE"
        discovery_source = "https://www.nj.gov/dca/news/news/2023/20230613.shtml"
        source_type = "municipal_ordinance"
        authoritative = False
        legal_control_confirmed = False

    class _Content:
        source_url = "https://example.gov/code"
        content = "§ 430-16 R-M(M) All accessory uses as permitted in the R-60 Zone. § 430-13 R-60 Private recreational facilities, including swimming pools, are permitted accessory uses."

    class _Query:
        def join(self, *_args): return self
        def filter(self, *_args): return self
        def all(self): return [(_Catalog(), _Content())]

    class _DB:
        def query(self, *_args): return _Query()

    result = analyze_dynamic_property(
        municipality="PERTH AMBOY CITY",
        block="55",
        lot="14",
        geometry={"rings": []},
        project_goal="pool",
        db=_DB(),
        zoning_analysis=lambda **_kwargs: {
            "status": "VERIFY",
            "candidate": {"record": {"zoning_district": "R-M(M)"}},
            "promotion": {"promotable": False},
        },
    )

    assert result["project_rule_candidate"]["status"] == "PROJECT_RULES_CANDIDATE"
    assert result["project_rule_candidate"]["authoritative"] is False
    assert result["project_applicability"]["reason"] == "DYNAMIC_ZONING_NOT_PROMOTABLE"
