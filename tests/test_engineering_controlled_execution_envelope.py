from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace
def job():
    return SimpleNamespace(sections={},job_number="ENG-12101",project_name="Controlled Execution Envelope Test",
        project_type="SITE",source="TEST",property_address="1 Envelope Way",client_id="CLIENT-1",
        state="ACTIVE",version=12,events=[])
def test_execution_envelope_has_exact_controlled_context():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["controlled_execution_envelope"]
    assert e["schema"]=="midra.engineering.controlled_execution_envelope"
    assert e["schema_version"]=="1.0"
    assert e["required_fields"]==[
        "operation_id","operation","target","actor_id","actor_type",
        "authorization_reference","authorization_state","execution_gate_state","prepared_at",
    ]
def test_envelope_is_immutable_handoff_not_execution():
    e=engineering_workspace(job())["agent_context"]["human_control"]["controlled_execution_envelope"]
    r=e["envelope_rules"]
    for key in ["execution_gate_must_be_eligible","authorization_state_must_be_authorized",
                "operation_identity_must_match","operation_must_match","target_must_match",
                "actor_must_match","authorization_reference_required",
                "envelope_is_immutable_after_preparation","envelope_is_not_execution",
                "envelope_may_not_expand_scope","envelope_may_not_grant_authority"]:
        assert r[key] is True
    assert e["missing_or_mismatched_envelope"]=="DENY"
def test_12_1_preserves_human_control_and_provider_boundary():
    a=engineering_workspace(job())["agent_context"]
    e=a["human_control"]["controlled_execution_envelope"]
    assert e["provider_may_rewrite_or_self_authorize_envelope"] is False
    assert e["professional_execution_envelope"]=="HUMAN_PROFESSIONAL_ONLY"
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
