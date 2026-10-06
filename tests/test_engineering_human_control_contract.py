from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-8901",project_name="Human Control Contract Test",
        project_type="SITE",source="TEST",property_address="1 Control Way",client_id="CLIENT-1",
        state="ACTIVE",version=8,events=[])

def test_human_control_defaults_are_fail_closed():
    a=engineering_workspace(job())["agent_context"]; h=a["human_control"]
    assert h["control_owner"]=="MIDRA_USER"
    assert h["ai_provider_authority"]=="NONE"
    assert h["authorization_model"]=="EXPLICIT_SCOPED"
    assert set(h["authorization_defaults"].values())=={"DENY"}
    assert h["authorization_rules"]["must_identify_operation"] is True
    assert h["authorization_rules"]["must_identify_target"] is True
    assert h["authorization_rules"]["may_not_be_inferred_from_prior_approval"] is True
    assert h["authorization_rules"]["may_not_expand_scope"] is True

def test_control_contract_is_model_agnostic_and_auditable():
    h=engineering_workspace(job())["agent_context"]["human_control"]
    assert h["provider_portability"]["model_agnostic"] is True
    assert h["provider_portability"]["provider_may_not_override_midra_policy"] is True
    assert h["provider_portability"]["provider_may_not_be_source_of_truth"] is True
    assert all(h["audit_requirements"].values())

def test_8_9_does_not_expand_ai_execution_authority():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["agent_contract"]["unknown_operation"]=="DENY"
    assert a["operation_policy"]["PROFESSIONAL_APPROVAL"]["classification"]=="HUMAN_PROFESSIONAL_ONLY"
