from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-13201",project_name="Reasoning Freedom Test",
        project_type="SITE",source="TEST",property_address="1 Reasoning Way",client_id="CLIENT-1",
        state="ACTIVE",version=13,events=[])
def human():
    return engineering_workspace(job())["agent_context"]["human_control"]
def test_reasoning_space_allows_open_ended_ideation():
    r=human()["intelligence_reasoning_space"]
    assert r["schema"]=="midra.engineering.intelligence_reasoning_space"
    assert r["mode"]=="ADVISORY"
    assert r["purpose"]=="OPEN_ENDED_REASONING_AND_IDEATION"
    assert all(r["freedoms"].values())
    assert r["design_rule"]=="MAXIMIZE_REASONING_FREEDOM_WHILE_PRESERVING_TRUTH_SECURITY_AND_ACTION_CONTROL"
def test_focus_queue_is_explicitly_not_the_reasoning_boundary():
    r=human()["intelligence_reasoning_space"]["interpretation"]
    assert r["focus_queue_is_recorded_midra_attention"] is True
    assert r["focus_queue_is_not_reasoning_boundary"] is True
    assert r["unrecorded_idea_may_be_proposed"] is True
    assert r["unrecorded_idea_must_not_be_claimed_as_existing_record"] is True
def test_reasoning_freedom_preserves_truth_security_action_and_professional_boundaries():
    r=human()["intelligence_reasoning_space"]
    assert r["provenance"]["ai_generated_idea"]=="MUST_NOT_BE_PRESENTED_AS_EXISTING_RECORD"
    a=r["action_boundary"]
    assert a["reasoning_does_not_require_action_authority"] is True
    assert a["creating_an_idea_does_not_change_project_state"] is True
    assert a["consequential_actions_use_existing_control_chain"] is True
    assert a["security_controls_remain_enforced"] is True
    assert a["professional_authority_remains_human"] is True
    assert a["ai_provider_cannot_self_authorize"] is True
def test_verified_13_1_focus_queue_contract_is_unchanged():
    q=human()["intelligence_focus_queue"]
    assert q["rules"]=={
        "recorded_attention_only":True,
        "preserve_existing_attention_order":True,
        "no_invented_tasks":True,
        "no_state_change":True,
        "no_authorization_granted":True,
        "no_professional_judgment":True,
    }
