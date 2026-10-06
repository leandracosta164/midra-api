from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11901",project_name="Authorization Binding Test",
        project_type="SITE",source="TEST",property_address="1 Binding Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_authorization_binding_requires_review_and_exact_authorization_context():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["controlled_action_authorization_binding"]
    assert b["schema"]=="midra.engineering.controlled_action_authorization_binding"
    assert b["schema_version"]=="1.0"
    assert b["required_bindings"]==[
        "operation_id","review_decision","authorized_operation","authorized_target",
        "authorized_actor","authorization_state",
    ]
def test_approved_review_still_requires_separate_explicit_authorization():
    b=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_authorization_binding"]
    r=b["binding_rules"]
    for key in ["review_decision_must_be_approve","authorization_must_be_separate_and_explicit",
                "operation_id_must_match","operation_must_match","target_must_match",
                "actor_must_match","authorization_state_must_be_authorized",
                "binding_may_not_expand_scope","binding_may_not_transfer","binding_may_not_grant_authority"]:
        assert r[key] is True
    assert b["missing_or_mismatched_binding"]=="DENY"
def test_11_9_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["controlled_action_authorization_binding"]
    assert b["provider_may_create_or_override_authorization_binding"] is False
    assert b["professional_authorization_binding"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
