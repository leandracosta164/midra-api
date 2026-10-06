from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10501",project_name="Delegation Lifecycle Test",
        project_type="SITE",source="TEST",property_address="1 Lifecycle Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_delegation_lifecycle_has_finite_explicit_states():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_lifecycle"]
    assert d["schema"]=="midra.engineering.delegation_lifecycle"
    assert d["schema_version"]=="1.0"
    assert d["states"]==["NOT_DELEGATED","ACTIVE","CONSUMED","REVOKED","EXPIRED"]
    assert d["initial_state"]=="NOT_DELEGATED"
    assert d["terminal_states"]==["CONSUMED","REVOKED","EXPIRED"]
    assert d["invalid_or_unknown_state"]=="DENY"

def test_delegation_cannot_persist_or_reactivate_implicitly():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["delegation_lifecycle"]["lifecycle_rules"]
    assert r["explicit_activation_required"] is True
    assert r["active_state_required_for_use"] is True
    assert r["may_be_revoked_before_use"] is True
    assert r["consumed_after_authorized_use"] is True
    assert r["terminal_state_may_not_be_used"] is True
    assert r["automatic_renewal"] is False
    assert r["prior_delegation_may_not_reactivate"] is False

def test_10_5_provider_cannot_change_delegation_state_or_gain_authority():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_lifecycle"]
    assert d["provider_may_change_delegation_state"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
