from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11801",project_name="Controlled Action Review Decision Test",
        project_type="SITE",source="TEST",property_address="1 Decision Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_review_decision_has_explicit_states_and_traceable_actor():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["controlled_action_review_decision"]
    assert d["schema"]=="midra.engineering.controlled_action_review_decision"
    assert d["schema_version"]=="1.0"
    assert d["decision_states"]==["APPROVE","REJECT","RETURN_FOR_CORRECTION"]
    assert d["required_fields"]==["operation_id","decision","decided_by","decided_at"]
def test_approval_may_proceed_but_is_not_authorization():
    d=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_review_decision"]
    r=d["decision_rules"]
    for key in ["human_decision_required","review_state_must_be_ready_for_decision",
                "operation_identity_must_match","approve_may_proceed_to_authorization",
                "approve_is_not_authorization","reject_may_not_proceed",
                "return_for_correction_may_not_proceed","decision_may_not_execute",
                "decision_may_not_expand_scope","decision_may_not_grant_authority"]:
        assert r[key] is True
    assert d["missing_or_invalid_decision"]=="DENY"
def test_11_8_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["controlled_action_review_decision"]
    assert d["provider_may_make_human_decision"] is False
    assert d["professional_decision"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
