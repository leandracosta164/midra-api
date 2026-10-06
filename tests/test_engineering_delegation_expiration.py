from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-11201",project_name="Delegation Expiration Test",
        project_type="SITE",source="TEST",property_address="1 Expiration Way",client_id="CLIENT-1",
        state="ACTIVE",version=11,events=[])
def test_expiration_requires_traceable_time_boundary():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["delegation_expiration"]
    assert e["schema"]=="midra.engineering.delegation_expiration"
    assert e["schema_version"]=="1.0"
    assert e["required_fields"]==["operation_id","delegated_by","delegated_to","effective_at","expires_at"]
def test_expired_delegation_cannot_execute_renew_or_reactivate():
    e=engineering_workspace(job())["agent_context"]["human_control"]["delegation_expiration"]
    r=e["expiration_rules"]
    assert r["expires_at_required"] is True
    assert r["expires_at_after_effective_at"] is True
    assert r["expired_delegation_may_not_execute"] is True
    assert r["expiration_is_automatic_at_boundary"] is True
    assert r["automatic_renewal"] is False
    assert r["expired_delegation_may_not_reactivate"] is True
    assert r["new_explicit_delegation_required_after_expiration"] is True
    assert r["expiration_preserves_history"] is True
    assert r["expiration_may_not_grant_authority"] is True
    assert e["missing_or_invalid_expiration"]=="DENY"
def test_11_2_preserves_provider_and_professional_boundaries():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["delegation_expiration"]
    assert e["provider_may_extend_or_renew_delegation"] is False
    assert e["professional_expiration"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
