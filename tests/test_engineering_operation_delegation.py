from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10401",project_name="Delegation Test",
        project_type="SITE",source="TEST",property_address="1 Delegation Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_operation_delegation_requires_explicit_scoped_record():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["operation_delegation"]
    assert d["schema"]=="midra.engineering.operation_delegation"
    assert d["schema_version"]=="1.0"
    assert d["required_fields"]==[
        "delegated_by","delegated_to","operation","target","delegated_at",
    ]
    assert d["missing_or_invalid_delegation"]=="DENY"

def test_delegation_cannot_expand_or_chain_authority():
    a=engineering_workspace(job())["agent_context"]
    r=a["human_control"]["operation_delegation"]["delegation_rules"]
    assert r["explicit_delegation_required"] is True
    assert r["operation_specific"] is True
    assert r["target_specific"] is True
    assert r["delegate_may_not_expand_scope"] is True
    assert r["delegate_may_not_redelegate"] is True
    assert r["delegation_may_be_revoked"] is True
    assert r["delegation_may_not_exceed_delegator_authority"] is True
    assert r["prior_delegation_may_not_be_inferred"] is True

def test_10_4_preserves_professional_and_provider_boundaries():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["operation_delegation"]
    assert d["professional_delegation"]=="HUMAN_PROFESSIONAL_ONLY"
    assert d["provider_may_create_delegation"] is False
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
