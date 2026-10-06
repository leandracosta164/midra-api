from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-13101",project_name="Focus Queue Test",
        project_type="SITE",source="TEST",property_address="1 Focus Way",client_id="CLIENT-1",
        state="ACTIVE",version=13,events=[])
def test_focus_queue_reuses_existing_attention_without_inventing_work():
    a=engineering_workspace(job())["agent_context"]
    q=a["human_control"]["intelligence_focus_queue"]
    expected=a["attention"].get("items",[]) if isinstance(a["attention"],dict) else []
    assert q["schema"]=="midra.engineering.intelligence_focus_queue"
    assert q["mode"]=="READ_ONLY"
    assert q["purpose"]=="PRIORITIZED_OPERATIONAL_FOCUS"
    assert q["source"]=="attention_summary"
    assert q["items"]==expected
    assert q["item_count"]==len(expected)
def test_focus_queue_preserves_source_order_and_human_control():
    q=engineering_workspace(job())["agent_context"]["human_control"]["intelligence_focus_queue"]
    r=q["rules"]
    assert r=={
        "recorded_attention_only":True,
        "preserve_existing_attention_order":True,
        "no_invented_tasks":True,
        "no_state_change":True,
        "no_authorization_granted":True,
        "no_professional_judgment":True,
    }
def test_future_intelligence_can_explain_and_propose_but_not_execute():
    q=engineering_workspace(job())["agent_context"]["human_control"]["intelligence_focus_queue"]
    u=q["agent_use"]
    assert u["may_explain_focus"] is True
    assert u["may_summarize_focus"] is True
    assert u["may_propose_response"] is True
    assert u["may_reorder_source_of_truth"] is False
    assert u["may_execute"] is False
