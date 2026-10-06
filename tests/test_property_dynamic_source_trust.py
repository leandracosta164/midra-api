from app.services.property_dynamic_source_trust import build_dynamic_source_trust_summary
from app.services.property_engineering_proposal_context import build_dynamic_engineering_handoff_summary


def test_discovered_but_unconfirmed_source_stays_verify():
    result=build_dynamic_source_trust_summary({
        "dynamic_promotable":False,
        "zoning":{
            "refresh":{"status":"DCA_SOURCES_DISCOVERED","registered":True,"canonical_name":"Example City"},
            "official_representation":{"status":"OFFICIAL_REPRESENTATION_ORCHESTRATION_COMPLETE","promoted_count":0},
            "legal_control":{"status":"LEGAL_CONTROL_ORCHESTRATION_COMPLETE","promoted_count":0},
            "promotion":{"status":"VERIFY","promotable":False,"reason":"SOURCE_AUTHORITY_NOT_CONFIRMED"},
            "candidate":{"record":{"source":{"current_status":"CURRENT","last_checked_at":"2026-10-03T10:00:00Z"}}},
        },
    })
    assert result["trust_state"]=="SOURCE_DISCOVERED_VERIFY"
    assert result["verification_required"] is True
    assert result["official_representation"]["confirmed"] is False
    assert result["legal_control"]["confirmed"] is False
    assert result["source_currentness"]["current_status"]=="CURRENT"


def test_fully_guarded_source_is_promotable_evidence():
    result=build_dynamic_source_trust_summary({
        "dynamic_promotable":True,
        "zoning":{
            "refresh":{"status":"DCA_SOURCES_DISCOVERED","registered":True},
            "official_representation":{"promoted_count":1},
            "legal_control":{"promoted_count":1},
            "promotion":{"status":"ZONING_RESOLVED","promotable":True},
            "candidate":{"record":{"source":{"authoritative":True,"legal_control_confirmed":True}}},
        },
    })
    assert result["trust_state"]=="PROMOTABLE_EVIDENCE"
    assert result["verification_required"] is False
    assert result["promotion"]["promotable"] is True


def test_authority_without_legal_control_explains_verify():
    result=build_dynamic_source_trust_summary({
        "dynamic_promotable":False,
        "zoning":{
            "refresh":{"status":"DCA_SOURCES_DISCOVERED","registered":True},
            "official_representation":{"promoted_count":1},
            "legal_control":{"promoted_count":0},
            "promotion":{"status":"VERIFY","promotable":False,"reason":"LEGAL_CONTROL_NOT_CONFIRMED"},
            "candidate":{"record":{"source":{"authoritative":True}}},
        },
    })
    assert result["trust_state"]=="AUTHORITY_CONFIRMED_LEGAL_CONTROL_VERIFY"
    assert "LEGAL_CONTROL_NOT_CONFIRMED" in result["verification_reasons"]


def test_proposal_handoff_carries_compact_trust_state():
    dynamic={
        "status":"DYNAMIC_ANALYSIS_COMPLETE","dynamic_promotable":False,
        "zoning":{"candidate":{"record":{"zoning_district":"R-1"}},"promotion":{"status":"VERIFY","promotable":False}},
        "project_applicability":{"status":"VERIFY","promotable":False},
        "approval_pathway":{"status":"VERIFY","promotable":False},
        "source_trust_summary":{
            "trust_state":"SOURCE_DISCOVERED_VERIFY","verification_required":True,
            "official_representation":{"confirmed":False},"legal_control":{"confirmed":False},
            "source_currentness":{"current_status":"CURRENT","last_checked_at":"2026-10-03T10:00:00Z"},
        },
    }
    summary=build_dynamic_engineering_handoff_summary({"dynamic_intelligence":dynamic})
    assert summary["source_trust"]["trust_state"]=="SOURCE_DISCOVERED_VERIFY"
    assert summary["source_trust"]["authority_confirmed"] is False
    assert summary["source_trust"]["legal_control_confirmed"] is False
