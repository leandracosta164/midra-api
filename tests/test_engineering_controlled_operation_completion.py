from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10001",project_name="Controlled Completion Test",
        project_type="SITE",source="TEST",property_address="1 Completion Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_controlled_operation_completion_requires_closed_control_loop():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_operation_completion"]
    assert c["schema"]=="midra.engineering.controlled_operation_completion"
    assert c["schema_version"]=="1.0"
    assert c["required_conditions"]==[
        "authorization_was_valid","execution_receipt_present","execution_result_recorded",
        "authorization_consumed","verification_state_verified","no_open_discrepancy",
    ]
    assert c["completion_states"]==["INCOMPLETE","COMPLETE","REQUIRES_REVIEW"]

def test_completion_does_not_overclaim_professional_or_agency_status():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_operation_completion"]
    r=c["completion_rules"]
    assert r["default_state"]=="INCOMPLETE"
    assert r["all_required_conditions_for_complete"] is True
    assert r["open_discrepancy_state"]=="REQUIRES_REVIEW"
    assert r["missing_evidence_state"]=="INCOMPLETE"
    assert r["completion_may_not_imply_professional_approval"] is True
    assert r["completion_may_not_imply_agency_acceptance"] is True
    assert r["completion_may_not_grant_new_authority"] is True

def test_10_0_preserves_human_professional_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["controlled_operation_completion"]
    assert c["professional_completion"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
