from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9201",project_name="Authorization Audit Test",
        project_type="SITE",source="TEST",property_address="1 Audit Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_authorization_audit_contract_requires_traceable_evidence():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["authorization_audit_contract"]
    assert c["schema"]=="midra.engineering.authorization_audit"
    assert c["schema_version"]=="1.0"
    assert c["record_required_for"]==["STATE_CHANGE","EXTERNAL_ACTION","ISSUE_OR_SUBMIT"]
    assert c["required_evidence"]==[
        "operation","target","authorized_by","authorized_at","actor","executed_at","result"
    ]

def test_authorization_audit_contract_prohibits_silent_execution():
    a=engineering_workspace(job())["agent_context"]
    c=a["human_control"]["authorization_audit_contract"]
    r=c["recording_rules"]
    assert r["record_before_and_after_state_when_applicable"] is True
    assert r["record_authorization_reference"] is True
    assert r["record_provider_when_ai_assisted"] is True
    assert r["record_failure_result"] is True
    assert r["silent_execution"] is False
    assert c["professional_approval_record"]=="HUMAN_PROFESSIONAL_ONLY"

def test_9_2_still_grants_no_execution_authority():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["authorization_requirements"]["missing_or_invalid_authorization"]=="DENY"
