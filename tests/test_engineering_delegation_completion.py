from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11401",project_name="Delegation Completion Test",
        project_type="SITE",source="TEST",property_address="1 Completion Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_delegation_completion_has_explicit_states_and_conditions():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["delegation_completion"]
    assert c["schema"]=="midra.engineering.delegation_completion"
    assert c["schema_version"]=="1.0"
    assert c["completion_states"]==["INCOMPLETE","COMPLETE","REQUIRES_REVIEW"]
    assert c["required_conditions"]==[
        "delegation_record_present","delegation_identity_consistent",
        "delegation_terminal_state_recorded","operation_binding_consistent_when_used",
        "consumption_evidence_present_when_used","no_open_delegation_discrepancy",
    ]
def test_completion_is_fail_closed_read_only_and_non_authorizing():
    c=engineering_workspace(job())["agent_context"]["human_control"]["delegation_completion"]
    r=c["completion_rules"]
    assert r["default_state"]=="INCOMPLETE"
    assert r["all_required_conditions_for_complete"] is True
    assert r["open_discrepancy_state"]=="REQUIRES_REVIEW"
    assert r["missing_evidence_state"]=="INCOMPLETE"
    assert r["completion_is_read_only"] is True
    assert r["completion_may_not_reactivate_delegation"] is True
    assert r["completion_may_not_grant_authority"] is True
    assert r["completion_may_not_imply_professional_approval"] is True
def test_11_4_preserves_human_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["delegation_completion"]
    assert c["professional_completion"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
