from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12301",project_name="Controlled Execution Permit Test",
        project_type="SITE",source="TEST",property_address="1 Permit Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_execution_permit_has_lifecycle_and_traceable_fields():
    a=engineering_workspace(job())["agent_context"]
    p=a["human_control"]["controlled_execution_permit"]
    assert p["schema"]=="midra.engineering.controlled_execution_permit"
    assert p["schema_version"]=="1.0"
    assert p["permit_states"]==["NOT_ISSUED","ISSUED","CONSUMED","INVALIDATED"]
    assert p["required_fields"]==[
        "operation_id","operation","target","actor_id","authorization_reference",
        "preflight_state","issued_by","issued_at",
    ]
def test_permit_is_exact_single_use_and_consumed_on_attempt():
    p=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_permit"]
    r=p["permit_rules"]
    for key in ["preflight_must_be_cleared_for_execution_attempt","authorization_must_be_current",
                "operation_identity_must_match","operation_must_match","target_must_match",
                "actor_must_match","permit_is_single_use","permit_consumed_on_execution_attempt",
                "permit_cannot_be_reused","permit_cannot_expand_scope","permit_cannot_transfer",
                "permit_does_not_imply_success"]:
        assert r[key] is True
    assert p["missing_or_invalid_permit"]=="DENY"
def test_12_3_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    p=a["human_control"]["controlled_execution_permit"]
    assert p["provider_may_issue_restore_or_expand_permit"] is False
    assert p["professional_execution_permit"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
