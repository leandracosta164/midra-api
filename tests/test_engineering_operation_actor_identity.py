from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10301",project_name="Actor Identity Test",
        project_type="SITE",source="TEST",property_address="1 Actor Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_operation_actor_identity_requires_explicit_actor():
    a=engineering_workspace(job())["agent_context"]
    i=a["human_control"]["operation_actor_identity"]
    assert i["schema"]=="midra.engineering.operation_actor_identity"
    assert i["schema_version"]=="1.0"
    assert i["actor_types"]==["MIDRA_USER","AI_ASSISTED","SYSTEM"]
    assert i["required_fields"]==["actor_id","actor_type"]

def test_actor_identity_is_recorded_and_not_inferred():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["operation_actor_identity"]["identity_rules"]
    assert r["actor_id_required"] is True
    assert r["actor_type_required"] is True
    assert r["actor_identity_must_be_recorded"] is True
    assert r["actor_may_not_inherit_authorizer_identity"] is True
    assert r["ai_provider_is_not_authorizing_actor"] is True
    assert r["unknown_actor"]=="DENY"

def test_10_3_preserves_professional_identity_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    i=a["human_control"]["operation_actor_identity"]
    assert i["professional_actor"]=="HUMAN_PROFESSIONAL_ONLY"
    assert i["provider_may_impersonate_actor"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
