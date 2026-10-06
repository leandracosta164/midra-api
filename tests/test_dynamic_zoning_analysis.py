from app.services.dynamic_zoning_analysis import analyze_dynamic_zoning_candidate


def test_dynamic_analysis_refreshes_then_resolves_candidate_without_promoting():
    calls = []

    def refresh(municipality):
        calls.append(("refresh", municipality))
        return {"status": "SOURCES_REFRESHED", "canonical_name": "Perth Amboy City"}

    def resolve_candidate(**kwargs):
        calls.append(("resolve", kwargs["municipality"], kwargs["block"], kwargs["lot"]))
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "municipality": "Perth Amboy City",
                "block": "55",
                "lot": "1",
                "zoning_district": "R-60",
                "source": {"authoritative": False},
            },
        }

    def promote(candidate):
        assert candidate["status"] == "ZONING_CANDIDATE_RESOLVED"
        return {"status": "VERIFY", "promotable": False, "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED"}

    result = analyze_dynamic_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        db=object(),
        refresh_sources=refresh,
        resolve_candidate=resolve_candidate,
        promote_candidate=promote,
    )

    assert result["status"] == "VERIFY"
    assert result["candidate"]["record"]["zoning_district"] == "R-60"
    assert result["promotion"]["promotable"] is False
    assert calls == [("refresh", "Perth Amboy City"), ("resolve", "Perth Amboy City", "55", "1")]


def test_dynamic_analysis_refuses_missing_parcel_geometry_before_refresh():
    calls = []

    def refresh(_municipality):
        calls.append("refresh")
        return {}

    result = analyze_dynamic_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={},
        db=object(),
        refresh_sources=refresh,
    )

    assert result["status"] == "VERIFY"
    assert result["promotion"]["reason"] == "PARCEL_GEOMETRY_OR_IDENTITY_MISSING"
    assert calls == []


def test_dynamic_analysis_refuses_missing_municipality():
    result = analyze_dynamic_zoning_candidate(
        municipality="",
        block="55",
        lot="1",
        geometry={"rings": []},
        db=object(),
    )

    assert result["status"] == "VERIFY"
    assert result["promotion"]["reason"] == "MUNICIPALITY_MISSING"


def test_dynamic_analysis_exposes_candidate_provenance_without_promoting_it():
    def resolve_candidate(**kwargs):
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "municipality": "Perth Amboy City",
                "block": "55",
                "lot": "1",
                "zoning_district": "R-60",
                "evidence_type": "ARCGIS_SPATIAL_INTERSECTION",
                "source": {
                    "source_url": "https://example.test/zoning",
                    "authoritative": False,
                },
            },
        }

    result = analyze_dynamic_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        db=object(),
        refresh_sources=lambda _m: {"status": "SOURCES_REFRESHED"},
        resolve_candidate=resolve_candidate,
        promote_candidate=lambda _c: {
            "status": "VERIFY",
            "promotable": False,
            "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED",
        },
    )

    evidence = result["evidence"]
    assert evidence["candidate_status"] == "ZONING_CANDIDATE_RESOLVED"
    assert evidence["zoning_district"] == "R-60"
    assert evidence["evidence_type"] == "ARCGIS_SPATIAL_INTERSECTION"
    assert evidence["source"]["authoritative"] is False
    assert evidence["promotable"] is False
    assert evidence["status"] == "VERIFY"


def test_dynamic_analysis_evidence_stays_verify_when_no_candidate_exists():
    result = analyze_dynamic_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": []},
        db=object(),
        refresh_sources=lambda _m: {"status": "SOURCES_REFRESHED"},
        resolve_candidate=lambda **_kwargs: {
            "status": "ZONING_NOT_RESOLVED",
            "reason": "NO_UNIQUE_DYNAMIC_ZONING_CANDIDATE",
        },
        promote_candidate=lambda _c: {
            "status": "VERIFY",
            "promotable": False,
            "reason": "CANDIDATE_NOT_RESOLVED",
        },
    )

    assert result["evidence"]["status"] == "VERIFY"
    assert result["evidence"]["zoning_district"] is None
    assert result["evidence"]["promotable"] is False


def test_dynamic_analysis_runs_official_representation_before_candidate_resolution():
    calls = []

    def authority(**kwargs):
        calls.append(("authority", kwargs["municipality"]))
        return {"status": "OFFICIAL_REPRESENTATION_ORCHESTRATION_COMPLETE", "promoted_count": 1}

    def resolve(**kwargs):
        calls.append(("resolve", kwargs["municipality"]))
        return {"status": "ZONING_CANDIDATE_RESOLVED", "record": {"zoning_district": "R-M(M)", "source": {"authoritative": True}}}

    result = analyze_dynamic_zoning_candidate(
        municipality="Perth Amboy City", block="55", lot="14", geometry={"rings": [[]]}, db=object(),
        refresh_sources=lambda _m: {"status": "SOURCES_REFRESHED"},
        authority_orchestrator=authority,
        resolve_candidate=resolve,
        promote_candidate=lambda _c: {"status": "VERIFY", "promotable": False, "reason": "LEGAL_CONTROL_NOT_CONFIRMED"},
    )
    assert calls == [("authority", "Perth Amboy City"), ("resolve", "Perth Amboy City")]
    assert result["official_representation"]["promoted_count"] == 1


def test_dynamic_analysis_runs_legal_control_after_official_representation_before_resolution():
    calls = []

    def authority(**kwargs):
        calls.append(("authority", kwargs["municipality"]))
        return {"status": "OFFICIAL_REPRESENTATION_ORCHESTRATION_COMPLETE", "promoted_count": 1}

    def legal(**kwargs):
        calls.append(("legal", kwargs["municipality"]))
        return {"status": "LEGAL_CONTROL_ORCHESTRATION_COMPLETE", "promoted_count": 1}

    def resolve(**kwargs):
        calls.append(("resolve", kwargs["municipality"]))
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "zoning_district": "R-M(M)",
                "source": {"authoritative": True, "legal_control_confirmed": True},
            },
        }

    result = analyze_dynamic_zoning_candidate(
        municipality="PERTH AMBOY CITY",
        block="55",
        lot="14",
        geometry={"rings": [[]]},
        db=object(),
        refresh_sources=lambda _m: {"status": "SOURCES_REFRESHED", "canonical_name": "Perth Amboy City"},
        authority_orchestrator=authority,
        legal_control_orchestrator=legal,
        resolve_candidate=resolve,
        promote_candidate=lambda _c: {"status": "OK", "promotable": True, "reason": "DYNAMIC_ZONING_PROMOTABLE"},
    )

    assert calls == [
        ("authority", "Perth Amboy City"),
        ("legal", "Perth Amboy City"),
        ("resolve", "PERTH AMBOY CITY"),
    ]
    assert result["legal_control"]["promoted_count"] == 1
    assert result["promotion"]["promotable"] is True
