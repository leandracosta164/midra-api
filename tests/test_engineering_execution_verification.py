from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9801",project_name="Execution Verification Test",
        project_type="SITE",source="TEST",property_address="1 Verification Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_execution_verification_requires_receipt_scope_result_and_state_checks():
    a=engineering_workspace(job())["agent_context"]
    v=a["human_control"]["execution_verification"]
    assert v["schema"]=="midra.engineering.execution_verification"
    assert v["schema_version"]=="1.0"
    assert v["verification_states"]==["NOT_VERIFIED","VERIFIED","DISCREPANCY"]
    assert v["required_checks"]==[
        "receipt_present","receipt_matches_authorized_operation",
        "receipt_matches_authorized_target","recorded_result_present",
        "recorded_state_matches_result_when_applicable",
    ]

def test_execution_verification_does_not_infer_success_or_authority():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["execution_verification"]["verification_rules"]
    assert r["default_state"]=="NOT_VERIFIED"
    assert r["all_checks_required_for_verified"] is True
    assert r["failed_check_state"]=="DISCREPANCY"
    assert r["missing_check_state"]=="NOT_VERIFIED"
    assert r["verification_may_not_change_execution_result"] is True
    assert r["verification_may_not_grant_authority"] is True

def test_9_8_preserves_professional_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    v=a["human_control"]["execution_verification"]
    assert v["professional_verification"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
