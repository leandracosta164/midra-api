from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10201",project_name="Operation Identity Test",
        project_type="SITE",source="TEST",property_address="1 Identity Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_operation_identity_requires_stable_operation_reference():
    a=engineering_workspace(job())["agent_context"]
    i=a["human_control"]["operation_identity"]
    assert i["schema"]=="midra.engineering.operation_identity"
    assert i["schema_version"]=="1.0"
    assert i["required_fields"]==["operation_id","operation","target","created_at"]
    assert i["identity_mismatch"]=="DENY"

def test_operation_identity_is_immutable_across_control_chain():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["operation_identity"]["binding_rules"]
    assert r["operation_id_unique"] is True
    assert r["operation_id_immutable"] is True
    assert r["operation_immutable_after_authorization"] is True
    assert r["target_immutable_after_authorization"] is True
    assert r["same_identity_required_for_receipt"] is True
    assert r["same_identity_required_for_verification"] is True
    assert r["same_identity_required_for_completion"] is True

def test_10_2_provider_cannot_replace_identity_or_gain_authority():
    a=engineering_workspace(job())["agent_context"]
    i=a["human_control"]["operation_identity"]
    assert i["provider_may_replace_identity"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
