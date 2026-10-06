from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11701",project_name="Controlled Action Review Test",
        project_type="SITE",source="TEST",property_address="1 Review Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_review_has_explicit_states_and_context_fields():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_review"]
    assert r["schema"]=="midra.engineering.controlled_action_review"
    assert r["schema_version"]=="1.0"
    assert r["review_states"]==["PENDING_HUMAN_REVIEW","READY_FOR_DECISION","REQUIRES_CORRECTION"]
    assert r["review_fields"]==[
        "operation_id","operation","target","actor_id","actor_type","requested_by",
        "requested_at","purpose","readiness_state",
    ]
def test_review_is_read_only_and_never_authorizes():
    r=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_review"]
    x=r["review_rules"]
    for key in ["request_identity_must_match","request_scope_must_match",
                "readiness_state_must_be_visible","missing_or_mismatched_context_requires_correction",
                "review_is_read_only","review_is_not_authorization","review_may_not_execute",
                "review_may_not_grant_authority","review_may_not_imply_professional_approval"]:
        assert x[key] is True
def test_11_7_preserves_human_decision_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["controlled_action_review"]
    assert r["provider_may_approve_from_review"] is False
    assert r["professional_review"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
