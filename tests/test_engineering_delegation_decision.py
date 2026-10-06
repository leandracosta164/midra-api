from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-10701",project_name="Delegation Decision Test",
        project_type="SITE",source="TEST",property_address="1 Decision Way",client_id="CLIENT-1",
        state="ACTIVE",version=10,events=[])

def test_delegation_decision_is_explicit_allow_or_deny():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_decision"]
    assert d["schema"]=="midra.engineering.delegation_decision"
    assert d["schema_version"]=="1.0"
    assert d["possible_decisions"]==["ALLOW","DENY"]
    assert d["allow_requires"]=="ALL_DELEGATION_VALIDATION_CHECKS_PASS"
    assert d["default_decision"]=="DENY"
    assert d["provider_may_override_decision"] is False

def test_delegation_decision_is_exact_and_single_use():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["delegation_decision"]
    assert d["deny_when"]==[
        "VALIDATION_FAILED","VALIDATION_MISSING","VALIDATION_UNKNOWN",
        "DELEGATION_NOT_ACTIVE","DELEGATION_NOT_CURRENT",
    ]
    s=d["decision_scope"]
    assert s["delegator_specific"] is True
    assert s["delegate_specific"] is True
    assert s["operation_specific"] is True
    assert s["target_specific"] is True
    assert s["single_use"] is True
    assert s["scope_expansion"] is False

def test_10_7_preserves_read_only_ai_boundary():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["delegation_validation"]["on_unknown_check"]=="DENY"
