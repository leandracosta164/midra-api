from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-13001",project_name="Operational Brief Test",
        project_type="SITE",source="TEST",property_address="1 Intelligence Way",client_id="CLIENT-1",
        state="ACTIVE",version=13,events=[])
def test_operational_brief_reuses_exact_existing_midra_project_truth():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["intelligence_operational_brief"]
    assert b["schema"]=="midra.engineering.intelligence_operational_brief"
    assert b["schema_version"]=="1.0"
    assert b["mode"]=="READ_ONLY"
    assert b["brief"]["project_ref"]==a["project_ref"]
    # Verified 12.9 names these agent-context projections brief/health/attention/next_move.
    assert b["brief"]["project_brief"]==a["brief"]
    assert b["brief"]["workflow_condition"]==a["health"].get("state","UNKNOWN")
    assert b["brief"]["next_move"]==a["next_move"]
    assert b["brief"]["attention"]==a["attention"]
def test_operational_brief_is_useful_without_action_authority():
    b=engineering_workspace(job())["agent_context"]["human_control"]["intelligence_operational_brief"]
    u=b["agent_use"]
    assert all(u[k] is True for k in ["may_read","may_analyze","may_summarize","may_propose_next_steps"])
    assert all(u[k] is False for k in ["may_invent_project_facts","may_change_project_state","may_authorize_action","may_execute_action","may_make_professional_approval"])
def test_operational_brief_preserves_source_of_truth_and_provider_compatibility():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["intelligence_operational_brief"]
    assert all(b["rules"][k] is True for k in ["recorded_midra_data_only","midra_remains_source_of_truth","missing_data_must_remain_unknown","no_inferred_approval_or_acceptance","controlled_actions_use_existing_control_chain"])
    assert a["human_control"]["agent_tool_access_manifest"]["future_provider_compatibility"]==["CLAUDE","OPENAI","OTHER_MODEL_PROVIDER"]
