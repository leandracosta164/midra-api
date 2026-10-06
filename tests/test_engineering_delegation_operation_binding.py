from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10801",project_name="Delegation Binding Test",
        project_type="SITE",source="TEST",property_address="1 Binding Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_delegation_binding_requires_operation_and_actor_identity():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["delegation_operation_binding"]
    assert b["schema"]=="midra.engineering.delegation_operation_binding"
    assert b["schema_version"]=="1.0"
    assert b["required_bindings"]==[
        "operation_id","delegator_actor_id","delegate_actor_id",
        "operation","target","delegation_decision",
    ]

def test_binding_cannot_transfer_to_another_operation():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["delegation_operation_binding"]
    r=b["binding_rules"]
    assert r["operation_id_must_match_controlled_operation"] is True
    assert r["delegator_must_match_delegation"] is True
    assert r["delegate_must_match_execution_actor"] is True
    assert r["operation_must_match_authorized_operation"] is True
    assert r["target_must_match_authorized_target"] is True
    assert r["decision_must_be_allow"] is True
    assert r["binding_is_single_operation"] is True
    assert r["binding_may_not_transfer"] is True
    assert b["missing_or_mismatched_binding"]=="DENY"

def test_10_8_preserves_provider_and_professional_boundaries():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["delegation_operation_binding"]
    assert b["provider_may_rebind_operation"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
