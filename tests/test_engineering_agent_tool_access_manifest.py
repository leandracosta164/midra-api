from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12901",project_name="Agent Tool Access Manifest Test",
        project_type="SITE",source="TEST",property_address="1 Tool Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_agent_tool_access_manifest_is_model_agnostic():
    a=engineering_workspace(job())["agent_context"]
    m=a["human_control"]["agent_tool_access_manifest"]
    assert m["schema"]=="midra.engineering.agent_tool_access_manifest"
    assert m["schema_version"]=="1.0"
    assert m["access_modes"]==["READ","ANALYZE","PROPOSE","PREPARE","CONTROLLED_ACTION"]
    assert m["future_provider_compatibility"]==["CLAUDE","OPENAI","OTHER_MODEL_PROVIDER"]
def test_tool_contract_is_structured_without_granting_direct_authority():
    m=engineering_workspace(job())["agent_context"]["human_control"]["agent_tool_access_manifest"]
    assert m["tool_contract_requirements"]==[
        "tool_name","capability_class","input_schema","output_schema",
        "authorization_requirement","audit_requirement",
    ]
    r=m["access_rules"]
    for key in ["tools_expose_midra_capabilities_not_database_credentials",
                "tool_access_does_not_grant_authority",
                "tool_access_must_respect_capability_boundary",
                "controlled_actions_use_existing_control_chain",
                "professional_actions_remain_human_professional_only",
                "unknown_tools_denied",
                "provider_specific_credentials_not_required_by_contract",
                "provider_can_be_replaced_without_rewriting_business_rules"]:
        assert r[key] is True
def test_12_9_keeps_midra_in_control_while_preserving_future_agent_access():
    a=engineering_workspace(job())["agent_context"]
    m=a["human_control"]["agent_tool_access_manifest"]
    assert m["direct_database_authority"]=="NONE"
    assert m["ai_provider_authority"]=="NONE"
    assert a["capabilities"]["read_project_context"] is True
    assert a["capabilities"]["propose_next_steps"] is True
    assert a["capabilities"]["execute_professional_action"] is False
