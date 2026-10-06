from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12701",project_name="Controlled Action Status Test",
        project_type="SITE",source="TEST",property_address="1 Status Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_control_status_exposes_full_control_path():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["controlled_action_control_status"]
    assert s["schema"]=="midra.engineering.controlled_action_control_status"
    assert s["schema_version"]=="1.0"
    assert s["control_path"]==[
        "READINESS","REQUEST","REVIEW","REVIEW_DECISION","AUTHORIZATION_BINDING",
        "EXECUTION_GATE","EXECUTION_ENVELOPE","EXECUTION_PREFLIGHT","EXECUTION_PERMIT",
        "EXECUTION_ATTEMPT","EXECUTION_OUTCOME","VERIFICATION_HANDOFF",
        "EXECUTION_VERIFICATION","OPERATION_COMPLETION",
    ]
def test_control_status_is_evidence_bound_and_read_only():
    s=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_control_status"]
    assert s["status_fields"]==[
        "operation_id","operation","target","actor_id","readiness_state","review_decision",
        "authorization_state","execution_gate_state","preflight_state","permit_state",
        "attempt_state","outcome_state","verification_handoff_state","verification_state",
        "completion_state",
    ]
    r=s["status_rules"]
    assert r["unknown_or_missing_state"]=="NOT_RECORDED"
    for key in ["recorded_evidence_only","status_is_read_only","status_may_not_infer_authorization",
                "status_may_not_infer_success","status_may_not_infer_completion",
                "status_may_not_execute","status_may_not_grant_authority"]:
        assert r[key] is True
def test_12_7_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["controlled_action_control_status"]
    assert s["provider_may_promote_or_override_status"] is False
    assert s["professional_control_status"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
