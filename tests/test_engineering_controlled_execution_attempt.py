from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12401",project_name="Controlled Execution Attempt Test",
        project_type="SITE",source="TEST",property_address="1 Attempt Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_execution_attempt_has_atomic_states_and_evidence():
    a=engineering_workspace(job())["agent_context"]
    x=a["human_control"]["controlled_execution_attempt"]
    assert x["schema"]=="midra.engineering.controlled_execution_attempt"
    assert x["schema_version"]=="1.0"
    assert x["attempt_states"]==["NOT_ATTEMPTED","ATTEMPTED","DENIED"]
    assert x["required_evidence"]==[
        "operation_id","operation","target","actor_id","permit_state","attempted_at","attempt_result",
    ]
def test_attempt_requires_exact_issued_permit_and_records_result():
    x=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_attempt"]
    r=x["attempt_rules"]
    for key in ["permit_must_be_issued","operation_identity_must_match","operation_must_match",
                "target_must_match","actor_must_match","attempt_consumes_permit",
                "attempt_result_must_be_recorded","attempt_does_not_imply_success",
                "attempt_does_not_imply_verification","attempt_may_not_expand_scope",
                "attempt_may_not_grant_authority","missing_or_invalid_permit_denies_attempt"]:
        assert r[key] is True
def test_12_4_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    x=a["human_control"]["controlled_execution_attempt"]
    assert x["provider_may_self_authorize_or_bypass_attempt_boundary"] is False
    assert x["professional_execution_attempt"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
