from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11001",project_name="Delegation Status Test",
        project_type="SITE",source="TEST",property_address="1 Status Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_delegation_control_status_exposes_complete_chain():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["delegation_control_status"]
    assert s["schema"]=="midra.engineering.delegation_control_status"
    assert s["schema_version"]=="1.0"
    assert s["control_chain"]==["DELEGATE","ACTIVATE","VALIDATE","DECIDE","BIND_OPERATION","CONSUME"]
    assert s["status_fields"]==["delegation_state","delegator_actor_id","delegate_actor_id","operation_id","operation","target","decision","consumption_state"]
def test_delegation_status_is_read_only_and_evidence_bound():
    s=engineering_workspace(job())["agent_context"]["human_control"]["delegation_control_status"]
    r=s["projection_rules"]
    assert r["read_only"] is True
    assert r["recorded_evidence_only"] is True
    assert r["unknown_value"]=="UNKNOWN"
    assert r["missing_value"]=="NOT_RECORDED"
    assert r["may_not_infer_delegation"] is True
    assert r["may_not_infer_authority"] is True
    assert r["may_not_reactivate_consumed_delegation"] is True
    assert r["may_not_grant_authority"] is True
def test_11_0_preserves_human_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["delegation_control_status"]
    assert s["professional_delegation_status"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
