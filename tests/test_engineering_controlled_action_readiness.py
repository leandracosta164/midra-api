from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11501",project_name="Controlled Action Readiness Test",
        project_type="SITE",source="TEST",property_address="1 Readiness Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_readiness_has_explicit_states_and_required_signals():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_readiness"]
    assert r["schema"]=="midra.engineering.controlled_action_readiness"
    assert r["schema_version"]=="1.0"
    assert r["readiness_states"]==["NOT_READY","READY_FOR_HUMAN_AUTHORIZATION","REQUIRES_REVIEW"]
    assert r["required_signals"]==[
        "operation_identity_defined","actor_identity_defined","target_defined",
        "applicable_control_contracts_present","no_open_control_discrepancy",
    ]
def test_ready_means_ready_for_authorization_not_execution():
    r=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_readiness"]
    x=r["readiness_rules"]
    assert x["default_state"]=="NOT_READY"
    assert x["all_required_signals_for_ready"] is True
    assert x["open_discrepancy_state"]=="REQUIRES_REVIEW"
    assert x["missing_signal_state"]=="NOT_READY"
    assert x["ready_state_does_not_authorize_execution"] is True
    assert x["ready_state_requires_separate_explicit_authorization"] is True
    assert x["readiness_is_read_only"] is True
    assert x["readiness_may_not_grant_authority"] is True
    assert x["readiness_may_not_imply_professional_approval"] is True
def test_11_5_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_readiness"]
    assert r["provider_may_promote_readiness_to_authority"] is False
    assert r["professional_readiness"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
