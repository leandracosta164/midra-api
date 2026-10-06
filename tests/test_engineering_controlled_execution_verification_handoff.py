from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12601",project_name="Verification Handoff Test",
        project_type="SITE",source="TEST",property_address="1 Handoff Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_verification_handoff_has_explicit_states_and_evidence():
    a=engineering_workspace(job())["agent_context"]
    h=a["human_control"]["controlled_execution_verification_handoff"]
    assert h["schema"]=="midra.engineering.controlled_execution_verification_handoff"
    assert h["schema_version"]=="1.0"
    assert h["handoff_states"]==["NOT_READY_FOR_VERIFICATION","READY_FOR_VERIFICATION","REQUIRES_REVIEW"]
    assert h["required_evidence"]==[
        "operation_id","operation","target","actor_id","permit_consumed",
        "execution_attempt_recorded","execution_outcome_recorded","attempt_result","outcome_state",
    ]
def test_handoff_connects_evidence_to_existing_verification_without_verifying():
    h=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_verification_handoff"]
    r=h["handoff_rules"]
    for key in ["operation_identity_must_match","operation_must_match","target_must_match",
                "actor_must_match","permit_must_be_consumed","execution_attempt_must_be_recorded",
                "execution_outcome_must_be_recorded","attempt_and_outcome_must_agree",
                "mismatch_requires_review","handoff_is_not_verification",
                "handoff_may_not_change_outcome","handoff_may_not_grant_authority"]:
        assert r[key] is True
    assert h["missing_evidence_state"]=="NOT_READY_FOR_VERIFICATION"
    assert h["mismatched_evidence_state"]=="REQUIRES_REVIEW"
    assert h["next_control"]=="execution_verification"
def test_12_6_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    h=a["human_control"]["controlled_execution_verification_handoff"]
    assert h["provider_may_verify_rewrite_or_override_handoff"] is False
    assert h["professional_verification_handoff"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
