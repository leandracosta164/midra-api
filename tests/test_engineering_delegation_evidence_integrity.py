from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11301",project_name="Delegation Evidence Test",
        project_type="SITE",source="TEST",property_address="1 Evidence Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_delegation_integrity_requires_complete_evidence_chain():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["delegation_evidence_integrity"]
    assert e["schema"]=="midra.engineering.delegation_evidence_integrity"
    assert e["schema_version"]=="1.0"
    assert e["required_evidence"]==[
        "delegation_record","delegation_lifecycle_record","delegation_validation_record",
        "delegation_decision_record","operation_binding_record","consumption_or_terminal_state_record",
    ]
def test_integrity_requires_same_identity_scope_and_chronology():
    e=engineering_workspace(job())["agent_context"]["human_control"]["delegation_evidence_integrity"]
    r=e["integrity_rules"]
    for key in ["same_operation_id_required","same_delegator_required","same_delegate_required",
                "same_operation_required","same_target_required","chronological_consistency_required",
                "terminal_state_may_not_be_overwritten","evidence_may_not_be_silently_replaced",
                "integrity_check_may_not_grant_authority"]:
        assert r[key] is True
    assert e["on_missing_evidence"]=="NOT_VERIFIED"
    assert e["on_mismatched_evidence"]=="DISCREPANCY"
def test_11_3_preserves_provider_and_professional_boundaries():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["delegation_evidence_integrity"]
    assert e["provider_may_rewrite_evidence"] is False
    assert e["professional_evidence_integrity"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
