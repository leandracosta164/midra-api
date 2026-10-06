from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9601",project_name="Controlled Execution Test",
        project_type="SITE",source="TEST",property_address="1 Execution Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_controlled_execution_requires_allow_and_exact_scope():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_execution"]
    assert c["schema"]=="midra.engineering.controlled_execution"
    assert c["schema_version"]=="1.0"
    assert c["preconditions"]==[
        "authorization_decision_is_allow",
        "operation_matches_authorized_operation",
        "target_matches_authorized_target",
        "authorization_is_not_terminal",
    ]
    assert c["failed_or_unknown_precondition"]=="DENY"

def test_controlled_execution_is_bounded_and_audited():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_execution"]
    r=c["execution_rules"]
    assert r["execute_only_authorized_operation"] is True
    assert r["execute_only_authorized_target"] is True
    assert r["scope_expansion"] is False
    assert r["silent_execution"] is False
    assert r["record_result"] is True
    assert r["consume_authorization_after_attempt"] is True
    assert c["provider_may_self_authorize"] is False

def test_9_6_preserves_professional_and_current_execution_boundaries():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_execution"]
    assert c["professional_action_execution"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
