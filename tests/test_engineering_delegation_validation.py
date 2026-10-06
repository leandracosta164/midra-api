from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10601",project_name="Delegation Validation Test",
        project_type="SITE",source="TEST",property_address="1 Validation Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_delegation_validation_requires_exact_active_delegation():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_validation"]
    assert d["schema"]=="midra.engineering.delegation_validation"
    assert d["schema_version"]=="1.0"
    assert d["required_checks"]==[
        "delegation_present","delegation_state_is_active","delegator_identity_matches",
        "delegate_identity_matches","operation_matches","target_matches",
        "delegation_is_current","delegation_not_revoked","delegation_not_consumed",
        "delegation_not_expired",
    ]

def test_delegation_validation_is_fail_closed():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_validation"]
    assert d["decision_rule"]=="ALL_CHECKS_MUST_PASS"
    assert d["on_failed_check"]=="DENY"
    assert d["on_missing_check"]=="DENY"
    assert d["on_unknown_check"]=="DENY"
    assert d["provider_may_bypass_validation"] is False

def test_10_6_preserves_read_only_ai_boundary():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
