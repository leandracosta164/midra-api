from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace


def job(sections=None):
    return SimpleNamespace(
        sections=sections or {},
        job_number="ENG-8701",
        project_name="Agent Ready Test",
        project_type="SITE",
        source="TEST",
        property_address="1 Test Way",
        client_id="CLIENT-1",
        state="ACTIVE",
        version=8,
        events=[],
    )


def test_agent_context_reuses_existing_workflow_projections():
    w=engineering_workspace(job({
        "action_items":{"summary":{"items":[{
            "action_id":"A-1","title":"Review drainage","status":"OPEN",
            "priority":"HIGH","owner":"Engineer","due_at":"2026-09-21"
        }]}}
    }))
    a=w["agent_context"]
    assert a["schema"]=="midra.engineering.agent_context"
    assert a["schema_version"]=="1.0"
    assert a["mode"]=="READ_ONLY"
    assert a["brief"]==w["project_brief"]
    assert a["health"]==w["project_health"]
    assert a["attention"]==w["attention"]
    assert a["next_move"]==w["next_move"]
    assert a["project_ref"]["job_number"]=="ENG-8701"


def test_agent_context_preserves_professional_control():
    a=engineering_workspace(job())["agent_context"]
    assert a["guardrails"]=={
        "professional_actions_require_approval":True,
        "automatic_professional_completion":False,
        "automatic_issue_or_submission":False,
        "may_invent_project_work":False,
    }
    assert a["capabilities"]["read_project_context"] is True
    assert a["capabilities"]["propose_next_steps"] is True
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False


def test_agent_context_is_not_a_second_source_of_truth():
    w=engineering_workspace(job())
    a=w["agent_context"]
    assert a["brief"]["workflow_state"]=="CLEAR"
    assert a["next_move"]["type"]=="NONE"
    assert a["attention"]["count"]==0
