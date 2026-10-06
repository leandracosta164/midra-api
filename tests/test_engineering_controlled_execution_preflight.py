from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12201",project_name="Controlled Execution Preflight Test",
        project_type="SITE",source="TEST",property_address="1 Preflight Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_preflight_has_explicit_states_and_checks():
    a=engineering_workspace(job())["agent_context"]
    p=a["human_control"]["controlled_execution_preflight"]
    assert p["schema"]=="midra.engineering.controlled_execution_preflight"
    assert p["schema_version"]=="1.0"
    assert p["preflight_states"]==["NOT_CLEARED","CLEARED_FOR_EXECUTION_ATTEMPT","REQUIRES_REVIEW"]
    assert p["required_checks"]==[
        "execution_envelope_present","execution_envelope_immutable","execution_gate_is_eligible",
        "authorization_state_is_authorized","authorization_is_current","operation_identity_matches",
        "operation_matches","target_matches","actor_matches","no_open_control_discrepancy",
    ]
def test_preflight_is_fail_closed_single_attempt_and_not_execution():
    p=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_preflight"]
    r=p["preflight_rules"]
    assert r["default_state"]=="NOT_CLEARED"
    assert r["all_required_checks_must_pass"] is True
    assert r["failed_or_missing_check_state"]=="NOT_CLEARED"
    assert r["open_discrepancy_state"]=="REQUIRES_REVIEW"
    for key in ["clearance_is_single_attempt","clearance_is_not_execution",
                "clearance_may_not_bypass_controlled_execution_contract","preflight_is_read_only",
                "preflight_may_not_expand_scope","preflight_may_not_grant_authority"]:
        assert r[key] is True
def test_12_2_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    p=a["human_control"]["controlled_execution_preflight"]
    assert p["provider_may_clear_or_override_preflight"] is False
    assert p["professional_execution_preflight"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
