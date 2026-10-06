from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9701",project_name="Execution Receipt Test",
        project_type="SITE",source="TEST",property_address="1 Receipt Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_execution_receipt_requires_traceable_identity_and_result():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["execution_receipt"]
    assert r["schema"]=="midra.engineering.execution_receipt"
    assert r["schema_version"]=="1.0"
    assert r["required_fields"]==[
        "operation","target","authorization_reference","authorized_by",
        "actor","attempted_at","result",
    ]
    assert r["result_states"]==["SUCCEEDED","FAILED","DENIED"]

def test_execution_receipt_records_every_attempt_and_cannot_create_authority():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["execution_receipt"]
    rules=r["recording_rules"]
    assert rules["record_every_attempt"] is True
    assert rules["record_failure"] is True
    assert rules["record_denial"] is True
    assert rules["record_before_and_after_state_when_applicable"] is True
    assert rules["receipt_is_append_only"] is True
    assert rules["receipt_may_not_grant_authority"] is True
    assert r["missing_receipt_for_attempt"]=="CONTROL_VIOLATION"

def test_9_7_preserves_professional_and_ai_boundaries():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["execution_receipt"]
    assert r["professional_approval_receipt"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
