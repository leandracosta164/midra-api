from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11101",project_name="Delegation Revocation Test",
        project_type="SITE",source="TEST",property_address="1 Revocation Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_revocation_requires_traceable_identity_and_reason():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["delegation_revocation"]
    assert r["schema"]=="midra.engineering.delegation_revocation"
    assert r["schema_version"]=="1.0"
    assert r["required_fields"]==["operation_id","delegated_by","delegated_to","revoked_by","revoked_at","reason"]
def test_revocation_is_immediate_preserves_history_and_cannot_reactivate():
    r=engineering_workspace(job())["agent_context"]["human_control"]["delegation_revocation"]
    x=r["revocation_rules"]
    assert x["active_delegation_required"] is True
    assert x["revoker_authority_required"] is True
    assert x["revocation_is_immediate"] is True
    assert x["revocation_preserves_history"] is True
    assert x["revoked_delegation_may_not_execute"] is True
    assert x["revoked_delegation_may_not_reactivate"] is True
    assert x["revocation_may_not_expand_scope"] is True
    assert x["revocation_may_not_grant_authority"] is True
    assert r["missing_or_invalid_revocation"]=="DENY"
def test_11_1_preserves_provider_and_professional_boundaries():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["delegation_revocation"]
    assert r["provider_may_revoke_or_restore_delegation"] is False
    assert r["professional_revocation"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
