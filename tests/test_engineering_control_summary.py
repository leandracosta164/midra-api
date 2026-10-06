from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9001",project_name="Control Summary Test",
        project_type="SITE",source="TEST",property_address="1 Control Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_control_summary_is_compact_and_fail_closed():
    a=engineering_workspace(job())["agent_context"]
    s=a["human_control"]["control_summary"]
    assert s=={
        "mode":"HUMAN_CONTROLLED",
        "state_changes":"EXPLICIT_AUTHORIZATION_REQUIRED",
        "external_actions":"EXPLICIT_AUTHORIZATION_REQUIRED",
        "professional_actions":"HUMAN_PROFESSIONAL_ONLY",
        "unknown_actions":"DENY",
    }

def test_control_summary_does_not_expand_capabilities():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["agent_contract"]["unknown_operation"]=="DENY"
