from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10101",project_name="Operation Control Status Test",
        project_type="SITE",source="TEST",property_address="1 Status Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_operation_control_status_exposes_complete_governance_chain():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["operation_control_status"]
    assert s["schema"]=="midra.engineering.operation_control_status"
    assert s["schema_version"]=="1.0"
    assert s["control_chain"]==[
        "AUTHORIZE","VALIDATE","DECIDE","EXECUTE","RECEIPT","VERIFY",
        "RESOLVE_DISCREPANCY","COMPLETE",
    ]
    assert s["status_fields"]==[
        "authorization_state","decision","execution_result",
        "verification_state","discrepancy_state","completion_state",
    ]

def test_operation_control_status_is_read_only_and_evidence_bound():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["operation_control_status"]["projection_rules"]
    assert r["read_only"] is True
    assert r["recorded_evidence_only"] is True
    assert r["unknown_value"]=="UNKNOWN"
    assert r["missing_value"]=="NOT_RECORDED"
    assert r["may_not_infer_approval"] is True
    assert r["may_not_infer_agency_acceptance"] is True
    assert r["may_not_grant_authority"] is True

def test_10_1_preserves_professional_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["operation_control_status"]
    assert s["professional_status"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
