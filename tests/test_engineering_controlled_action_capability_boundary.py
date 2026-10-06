from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12801",project_name="Capability Boundary Test",
        project_type="SITE",source="TEST",property_address="1 Boundary Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_capability_boundary_classifies_future_agent_capabilities():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["controlled_action_capability_boundary"]
    assert b["schema"]=="midra.engineering.controlled_action_capability_boundary"
    assert b["schema_version"]=="1.0"
    c=b["capability_classes"]
    assert c["READ_CONTEXT"]=="READ_ONLY_ALLOWED"
    assert c["ANALYZE_CONTEXT"]=="READ_ONLY_ALLOWED"
    assert c["PROPOSE_ACTION"]=="PROPOSAL_ONLY"
    assert c["PREPARE_CONTROLLED_ACTION"]=="HUMAN_REVIEW_REQUIRED"
    assert c["AUTHORIZE_ACTION"]=="HUMAN_ONLY"
    assert c["EXECUTE_CONTROLLED_ACTION"]=="EXISTING_CONTROL_CHAIN_REQUIRED"
    assert c["PROFESSIONAL_APPROVAL"]=="HUMAN_PROFESSIONAL_ONLY"
    assert c["ISSUE_OR_SUBMIT"]=="HUMAN_AUTHORIZATION_REQUIRED"
def test_boundary_reuses_existing_control_chain_instead_of_new_lifecycle():
    b=engineering_workspace(job())["agent_context"]["human_control"]["controlled_action_capability_boundary"]
    chain=b["execution_control_chain"]
    for name in ["controlled_action_readiness","controlled_action_authorization_binding",
                 "controlled_execution_permit","controlled_execution_attempt",
                 "controlled_execution_outcome","controlled_execution_verification_handoff",
                 "execution_verification","controlled_operation_completion"]:
        assert name in chain
    r=b["boundary_rules"]
    for key in ["midra_is_source_of_truth","business_rules_remain_in_midra",
                "ai_provider_is_replaceable","unknown_capability_denied",
                "no_provider_self_authorization","no_provider_scope_expansion",
                "no_provider_professional_authority","no_second_execution_lifecycle",
                "future_agent_must_use_existing_control_chain"]:
        assert r[key] is True
def test_12_8_keeps_midra_and_human_in_control():
    a=engineering_workspace(job())["agent_context"]
    b=a["human_control"]["controlled_action_capability_boundary"]
    assert b["ai_provider_authority"]=="NONE"
    assert b["professional_authority"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
