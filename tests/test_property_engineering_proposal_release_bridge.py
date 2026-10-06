from app.services.property_engineering_proposal_release_bridge import release_property_engineering_proposal_to_client

def approved():
    return {"status":"APPROVED_READY_TO_SEND","send_allowed":True,"sent":False,"proposal_id":"MEP-1"}

def test_release_requires_engineering_identity():
    try:
        release_property_engineering_proposal_to_client(approved_snapshot=approved(),engineering_user="")
    except PermissionError:
        pass
    else:
        raise AssertionError("expected Engineering identity requirement")

def test_release_marks_separate_sent_state_without_client_approval_or_job():
    result=release_property_engineering_proposal_to_client(
        approved_snapshot=approved(),engineering_user="engineer@midra.test"
    )
    assert result["status"]=="SENT"
    assert result["sent"] is True
    assert result["send_allowed"] is False
    assert result["client_response_status"]=="AWAITING_CLIENT_RESPONSE"
    assert result["engineering_job_created"] is False
    assert result["professional_boundary"]["client_approved"] is False
