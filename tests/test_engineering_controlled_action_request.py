from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11601",project_name="Controlled Action Request Test",
        project_type="SITE",source="TEST",property_address="1 Request Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_action_request_has_explicit_identity_actor_and_purpose():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_request"]
    assert r["schema"]=="midra.engineering.controlled_action_request"
    assert r["schema_version"]=="1.0"
    assert r["required_fields"]==[
        "operation_id","operation","target","actor_id","actor_type",
        "requested_by","requested_at","purpose",
    ]
def test_request_is_bound_to_readiness_and_is_not_authorization():
    r=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_request"]
    x=r["request_rules"]
    for key in ["readiness_must_be_ready_for_human_authorization","operation_identity_must_match",
                "target_must_match","actor_identity_must_match","purpose_required",
                "request_is_not_authorization","request_may_not_execute",
                "request_may_not_expand_scope","request_may_not_grant_authority"]:
        assert x[key] is True
    assert r["missing_or_mismatched_request"]=="DENY"
def test_11_6_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_request"]
    assert r["provider_may_self_approve_request"] is False
    assert r["professional_request"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
