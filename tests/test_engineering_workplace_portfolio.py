from app.services.engineering_workplace_portfolio import classify_property_proposal_stage

def test_stage_pipeline_order():
    assert classify_property_proposal_stage()["stage"]=="AWAITING_PROPOSAL_DRAFT"
    assert classify_property_proposal_stage(has_draft=True)["stage"]=="AWAITING_ENGINEERING_REVIEW"
    assert classify_property_proposal_stage(has_review=True)["stage"]=="READY_FOR_CLIENT_RELEASE"
    assert classify_property_proposal_stage(has_release=True)["stage"]=="AWAITING_CLIENT_RESPONSE"
    assert classify_property_proposal_stage(client_response="ACCEPTED")["stage"]=="READY_FOR_JOB_CREATION"
    assert classify_property_proposal_stage(client_response="DECLINED")["stage"]=="CLIENT_DECLINED"
    assert classify_property_proposal_stage(engineering_job_number="26-001")["stage"]=="ENGINEERING_JOB_CREATED"

def test_job_creation_is_terminal_priority():
    state=classify_property_proposal_stage(
        has_draft=True,has_review=True,has_release=True,
        client_response="ACCEPTED",engineering_job_number="26-001"
    )
    assert state["stage"]=="ENGINEERING_JOB_CREATED"
    assert state["next_action"]=="OPEN_ENGINEERING_JOB"
