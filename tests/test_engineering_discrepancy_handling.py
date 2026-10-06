from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job():
    return SimpleNamespace(sections={},job_number="ENG-9901",project_name="Discrepancy Handling Test",
        project_type="SITE",source="TEST",property_address="1 Discrepancy Way",client_id="CLIENT-1",
        state="ACTIVE",version=9,events=[])

def test_discrepancy_handling_contains_and_surfaces_discrepancy():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["discrepancy_handling"]
    assert d["schema"]=="midra.engineering.discrepancy_handling"
    assert d["schema_version"]=="1.0"
    assert d["discrepancy_states"]==["OPEN","UNDER_REVIEW","RESOLVED"]
    rules=d["on_discrepancy"]
    assert rules["halt_automatic_continuation"] is True
    assert rules["preserve_execution_receipt"] is True
    assert rules["preserve_recorded_result"] is True
    assert rules["surface_for_human_review"] is True
    assert rules["automatic_retry"] is False
    assert rules["automatic_state_correction"] is False

def test_discrepancy_resolution_requires_traceable_human_record():
    a=engineering_workspace(job())["agent_context"]
    d=a["human_control"]["discrepancy_handling"]
    assert d["resolution_requirements"]==["resolution_recorded","resolved_by","resolved_at"]
    assert d["missing_or_unknown_resolution"]=="UNRESOLVED"
    assert d["professional_discrepancy_resolution"]=="HUMAN_PROFESSIONAL_ONLY"

def test_9_9_preserves_ai_and_professional_boundaries():
    a=engineering_workspace(job())["agent_context"]
    assert a["mode"]=="READ_ONLY"
    assert a["capabilities"]["execute_professional_action"] is False
    assert a["capabilities"]["issue_or_submit"] is False
    assert a["human_control"]["ai_provider_authority"]=="NONE"
    assert a["human_control"]["execution_verification"]["verification_rules"]["failed_check_state"]=="DISCREPANCY"
