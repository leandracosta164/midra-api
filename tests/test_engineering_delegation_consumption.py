from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10901",project_name="Delegation Consumption Test",
        project_type="SITE",source="TEST",property_address="1 Consumption Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_delegation_consumption_requires_traceable_attempt_evidence():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["delegation_consumption"]
    assert c["schema"]=="midra.engineering.delegation_consumption"
    assert c["schema_version"]=="1.0"
    assert c["consumption_trigger"]=="CONTROLLED_OPERATION_ATTEMPT"
    assert c["required_evidence"]==[
        "operation_id","delegator_actor_id","delegate_actor_id",
        "delegation_decision","attempted_at","result",
    ]

def test_delegation_is_consumed_after_attempt_and_cannot_be_reused():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["delegation_consumption"]
    r=c["consumption_rules"]
    assert r["allow_decision_required"] is True
    assert r["matching_operation_binding_required"] is True
    assert r["consume_after_attempt"] is True
    assert r["consume_on_success"] is True
    assert r["consume_on_failure"] is True
    assert r["consume_on_denied_execution_attempt"] is True
    assert r["consumed_delegation_may_not_be_reused"] is True
    assert r["consumption_may_not_expand_scope"] is True
    assert r["consumption_may_not_grant_authority"] is True
    assert c["missing_consumption_evidence"]=="CONTROL_VIOLATION"

def test_10_9_provider_cannot_restore_consumed_delegation():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["delegation_consumption"]
    assert c["provider_may_restore_consumed_delegation"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
