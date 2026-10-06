from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9101",project_name="Authorization Requirements Test",
        project_type="SITE",source="TEST",property_address="1 Authorization Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_authorization_requirements_are_explicit_and_scoped():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["authorization_requirements"]
    assert r["schema"]=="midra.engineering.authorization_requirements"
    assert r["schema_version"]=="1.0"
    assert r["required_fields"]==["operation","target","authorized_by","authorized_at"]
    s=r["scope_rules"]
    assert s["operation_required"] is True
    assert s["target_required"] is True
    assert s["actor_required"] is True
    assert s["timestamp_required"] is True
    assert s["authorization_must_be_current"] is True
    assert s["reuse_for_other_operation"] is False
    assert s["reuse_for_other_target"] is False
    assert r["missing_or_invalid_authorization"]=="DENY"

def test_9_1_contract_grants_no_execution_authority():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["control_summary"]["unknown_actions"]=="DENY"
