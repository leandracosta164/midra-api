from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-133R",project_name="Safety Posture Recovery",
        project_type="SITE",source="TEST",property_address="1 Open Way",client_id="CLIENT-1",
        state="ACTIVE",version=13,events=[])
def hc(): return engineering_workspace(job())["agent_context"]["human_control"]
def test_safety_only_posture_is_open_by_default():
    p=hc()["ai_safety_posture"]
    assert p["mode"]=="SAFETY_ONLY"
    assert p["default_capability_posture"]=="OPEN"
    assert all(p["interpretation"].values())
def test_only_safety_domains_are_added():
    assert hc()["ai_safety_posture"]["safety_scope"]==[
        "SECURITY_AND_CREDENTIAL_PROTECTION",
        "DATA_INTEGRITY_AND_TRUTHFUL_PROVENANCE",
        "DESTRUCTIVE_OR_CONSEQUENTIAL_ACTION_CONTROL",
        "AUTHORIZATION_AND_ACCESS_CONTROL",
        "LEGAL_AND_PROFESSIONAL_AUTHORITY",
    ]
def test_historical_contracts_remain_for_backward_compatibility():
    h=hc()
    assert "controlled_action_capability_boundary" in h
    assert "agent_tool_access_manifest" in h
    assert "intelligence_reasoning_space" in h
    assert "intelligence_focus_queue" in h
    assert "intelligence_operational_brief" in h
