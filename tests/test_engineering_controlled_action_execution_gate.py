from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12001",project_name="Execution Gate Test",
        project_type="SITE",source="TEST",property_address="1 Gate Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_execution_gate_has_explicit_states_and_conditions():
    a=engineering_workspace(job())["agent_context"]
    g=a["human_control"]["controlled_action_execution_gate"]
    assert g["schema"]=="midra.engineering.controlled_action_execution_gate"
    assert g["schema_version"]=="1.0"
    assert g["gate_states"]==["BLOCKED","ELIGIBLE_FOR_CONTROLLED_EXECUTION","REQUIRES_REVIEW"]
    assert g["required_conditions"]==[
        "review_decision_is_approve","authorization_binding_valid",
        "authorization_state_is_authorized","operation_identity_matches",
        "target_matches","actor_matches","no_open_control_discrepancy",
    ]
def test_gate_is_fail_closed_and_eligibility_is_not_execution():
    g=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_execution_gate"]
    r=g["gate_rules"]
    assert r["default_state"]=="BLOCKED"
    assert r["all_required_conditions_for_eligibility"] is True
    assert r["missing_condition_state"]=="BLOCKED"
    assert r["open_discrepancy_state"]=="REQUIRES_REVIEW"
    assert r["eligibility_is_not_execution"] is True
    assert r["eligibility_may_not_bypass_controlled_execution_contract"] is True
    assert r["gate_is_read_only"] is True
    assert r["gate_may_not_expand_scope"] is True
    assert r["gate_may_not_grant_authority"] is True
def test_12_0_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    g=a["human_control"]["controlled_action_execution_gate"]
    assert g["provider_may_open_or_override_gate"] is False
    assert g["professional_execution_gate"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
