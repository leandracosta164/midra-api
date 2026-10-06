from types import SimpleNamespace
from app.services.property_engineering_proposal_context import build_dynamic_engineering_handoff_summary, build_property_engineering_proposal_context

def _analysis(promotable=False):
    return {"dynamic_intelligence":{"status":"DYNAMIC_ANALYSIS_COMPLETE","dynamic_promotable":promotable,"zoning":{"candidate":{"record":{"zoning_district":"R-1"}},"promotion":{"status":"ZONING_RESOLVED" if promotable else "VERIFY","promotable":promotable}},"project_applicability":{"status":"APPLICABLE" if promotable else "VERIFY","promotable":promotable},"approval_pathway_candidate":{"primary_pathway":"SITE_PLAN_APPROVAL","reviewing_bodies":["PLANNING_BOARD"]},"approval_pathway":{"status":"AVAILABLE" if promotable else "VERIFY","promotable":promotable,"primary_pathway":"SITE_PLAN_APPROVAL" if promotable else None,"reviewing_bodies":["PLANNING_BOARD"] if promotable else []}},"verification_items":[]}

def test_verify_boundary():
    s=build_dynamic_engineering_handoff_summary(_analysis(False))
    assert s["available"] is True and s["verification_required"] is True
    assert s["approval_pathway"]["primary_pathway"]=="SITE_PLAN_APPROVAL"
    assert s["professional_boundary"]["engineer_reviewed"] is False

def test_promoted_context_is_not_professional_acceptance():
    s=build_dynamic_engineering_handoff_summary(_analysis(True))
    assert s["dynamic_promotable"] is True and s["verification_required"] is False
    assert s["professional_boundary"]["engineer_accepted"] is False

def test_no_dynamic_context_is_explicit():
    assert build_dynamic_engineering_handoff_summary({})=={"status":"NO_DYNAMIC_INTELLIGENCE","available":False,"verification_required":False}

def test_exact_context_includes_dynamic_summary():
    run=SimpleNamespace(analysis_run_id="a1",property_record_id="p1",analysis=_analysis(False))
    proposal=SimpleNamespace(proposal_request_id="r1",property_record_id="p1",request_status="REQUESTED")
    record=SimpleNamespace(property_record_id="p1")
    c=build_property_engineering_proposal_context(proposal_request=proposal,property_record=record,analysis_run=run)
    assert c["dynamic_intelligence_summary"]["verification_required"] is True
    assert c["engineering_job_created"] is False
