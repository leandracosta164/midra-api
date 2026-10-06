from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9401",project_name="Authorization Validation Test",
        project_type="SITE",source="TEST",property_address="1 Validation Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_authorization_validation_requires_every_gate():
    a=engineering_workspace(job())["agent_context"]
    v=a["human_control"]["authorization_validation"]
    assert v["schema"]=="midra.engineering.authorization_validation"
    assert v["schema_version"]=="1.0"
    assert v["required_checks"]==[
        "authorization_present","state_is_authorized","operation_matches","target_matches",
        "authorizing_actor_present","authorization_is_current","authorization_not_revoked",
        "authorization_not_consumed","authorization_not_expired",
    ]
    assert v["decision_rule"]=="ALL_CHECKS_MUST_PASS"

def test_authorization_validation_fails_closed():
    a=engineering_workspace(job())["agent_context"]
    v=a["human_control"]["authorization_validation"]
    assert v["on_failed_check"]=="DENY"
    assert v["on_missing_check"]=="DENY"
    assert v["on_unknown_check"]=="DENY"
    assert v["provider_may_bypass_validation"] is False

def test_9_4_preserves_human_control_and_no_execution_authority():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["authorization_lifecycle"]["invalid_or_unknown_state"]=="DENY"
