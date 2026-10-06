from app.services.engineering_workplace_portfolio import classify_property_proposal_stage, _proposal_timeline_event

def test_timeline_event_shape():
    item=_proposal_timeline_event(key="CLIENT_RELEASE",label="Proposal released",status="COMPLETE",detail="RELEASED")
    assert item["key"]=="CLIENT_RELEASE"
    assert item["status"]=="COMPLETE"
    assert item["detail"]=="RELEASED"
    assert item["occurred_at"] is None

def test_workplace_detail_preserves_next_actions():
    assert classify_property_proposal_stage(has_draft=True)["next_action"]=="REVIEW_PROPOSAL_DRAFT"
    assert classify_property_proposal_stage(has_review=True)["next_action"]=="RELEASE_PROPOSAL_TO_CLIENT"
    assert classify_property_proposal_stage(has_release=True)["next_action"]=="RECORD_CLIENT_RESPONSE"
    assert classify_property_proposal_stage(client_response="ACCEPTED")["next_action"]=="CREATE_ENGINEERING_JOB"
    assert classify_property_proposal_stage(engineering_job_number="26-001")["next_action"]=="OPEN_ENGINEERING_JOB"
