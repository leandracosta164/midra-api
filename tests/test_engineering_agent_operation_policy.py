from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace


def job():
    return SimpleNamespace(
        sections={},
        job_number="ENG-8801",
        project_name="Agent Boundary Test",
        project_type="SITE",
        source="TEST",
        property_address="1 Boundary Way",
        client_id="CLIENT-1",
        state="ACTIVE",
        version=8,
        events=[],
    )


def test_operation_policy_is_machine_readable_and_fail_closed():
    a=engineering_workspace(job())["agent_context"]
    policy=a["operation_policy"]

    assert policy["READ_PROJECT_CONTEXT"]=={
        "classification":"READ_ONLY_ALLOWED",
        "changes_project_state":False,
        "requires_human_approval":False,
    }
    assert policy["PROPOSE_NEXT_STEP"]["classification"]=="PROPOSAL_ONLY"
    assert policy["PROPOSE_NEXT_STEP"]["changes_project_state"] is False

    assert policy["MUTATE_PROJECT_RECORD"]["classification"]=="APPROVAL_REQUIRED"
    assert policy["MUTATE_PROJECT_RECORD"]["requires_human_approval"] is True
    assert policy["PROFESSIONAL_APPROVAL"]["classification"]=="HUMAN_PROFESSIONAL_ONLY"
    assert policy["ISSUE_OR_SUBMIT"]["classification"]=="HUMAN_AUTHORIZATION_REQUIRED"

    contract=a["agent_contract"]
    assert contract["default_effect"]=="NO_CHANGE"
    assert contract["unknown_operation"]=="DENY"
    assert contract["approval_must_be_explicit"] is True
    assert contract["recorded_workflow_is_source_of_truth"] is True


def test_8_8_does_not_grant_new_execution_capability():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["guardrails"]["professional_actions_require_approval"] is True
    assert a["guardrails"]["may_invent_project_work"] is False
