from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12501",project_name="Controlled Execution Outcome Test",
        project_type="SITE",source="TEST",property_address="1 Outcome Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_execution_outcome_has_states_and_traceable_evidence():
    a=engineering_workspace(job())["agent_context"]
    o=a["human_control"]["controlled_execution_outcome"]
    assert o["schema"]=="midra.engineering.controlled_execution_outcome"
    assert o["schema_version"]=="1.0"
    assert o["outcome_states"]==["NOT_RECORDED","SUCCEEDED","FAILED","DENIED"]
    assert o["required_evidence"]==[
        "operation_id","operation","target","actor_id","attempted_at","attempt_result","recorded_at",
    ]
def test_outcome_preserves_attempt_evidence_without_verifying_it():
    o=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_outcome"]
    r=o["outcome_rules"]
    for key in ["execution_attempt_must_be_recorded","operation_identity_must_match",
                "operation_must_match","target_must_match","actor_must_match",
                "outcome_must_match_attempt_result","failure_and_denial_must_be_preserved",
                "outcome_is_append_only","outcome_does_not_imply_verification",
                "outcome_does_not_imply_completion","outcome_may_not_grant_authority"]:
        assert r[key] is True
    assert o["missing_outcome_evidence"]=="NOT_RECORDED"
    assert o["mismatched_outcome_evidence"]=="DISCREPANCY"
def test_12_5_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    o=a["human_control"]["controlled_execution_outcome"]
    assert o["provider_may_rewrite_or_promote_outcome"] is False
    assert o["professional_execution_outcome"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
