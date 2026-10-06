from app.services.property_engineering_proposal_review_bridge import approve_property_engineering_proposal_draft

def draft():
    return {"proposal_id":"MEP-ABC","proposal_number":"P-2026-001","status":"DRAFT_REQUIRES_ENGINEER_REVIEW","scope_of_services":[{"service":"Site Plan","price":"2500.00"}],"total_price":"2500.00","source_product":"MIDRA_PROPERTY","property_record_id":"p1","property_proposal_request_id":"r1","analysis_id":"a1"}

def test_approval_uses_existing_engineering_workflow_and_preserves_boundary():
    result=approve_property_engineering_proposal_draft(draft_snapshot=draft(),engineering_user="eng@example.com")
    assert result["status"]=="APPROVED_READY_TO_SEND"
    assert result["approved_by"]=="eng@example.com"
    assert result["send_allowed"] is True
    assert result["sent"] is False
    assert result["engineering_job_created"] is False
    assert result["professional_boundary"]["proposal_engineer_approved"] is True
    assert result["professional_boundary"]["property_analysis_engineer_accepted"] is False

def test_review_refuses_non_review_draft():
    item=draft(); item["status"]="APPROVED_READY_TO_SEND"
    try: approve_property_engineering_proposal_draft(draft_snapshot=item,engineering_user="eng@example.com")
    except ValueError as exc: assert "review-required" in str(exc)
    else: raise AssertionError("non-draft approved")
