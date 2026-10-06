from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9301",project_name="Authorization Lifecycle Test",
        project_type="SITE",source="TEST",property_address="1 Lifecycle Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_authorization_lifecycle_is_explicit_and_finite():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["authorization_lifecycle"]
    assert c["schema"]=="midra.engineering.authorization_lifecycle"
    assert c["schema_version"]=="1.0"
    assert c["states"]==["NOT_AUTHORIZED","AUTHORIZED","CONSUMED","REVOKED","EXPIRED"]
    assert c["initial_state"]=="NOT_AUTHORIZED"
    assert c["terminal_states"]==["CONSUMED","REVOKED","EXPIRED"]
    assert c["invalid_or_unknown_state"]=="DENY"

def test_authorization_cannot_self_extend_or_reactivate():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["authorization_lifecycle"]["rules"]
    assert r["explicit_grant_required"] is True
    assert r["authorization_is_single_scope"] is True
    assert r["may_be_revoked_before_execution"] is True
    assert r["consumed_after_authorized_execution"] is True
    assert r["terminal_state_may_not_execute"] is True
    assert r["automatic_renewal"] is False
    assert r["prior_authorization_may_not_reactivate"] is False

def test_9_3_still_grants_no_execution_authority():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["authorization_requirements"]["missing_or_invalid_authorization"]=="DENY"
