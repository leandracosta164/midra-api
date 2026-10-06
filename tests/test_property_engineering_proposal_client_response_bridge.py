from app.services.property_engineering_proposal_client_response_bridge import (
    record_property_engineering_proposal_client_response,
)


def released():
    return {
        "status":"SENT",
        "sent":True,
        "proposal_id":"MEP-1",
        "client_response_status":"AWAITING_CLIENT_RESPONSE",
        "engineering_job_created":False,
    }


def test_client_response_requires_engineering_identity():
    try:
        record_property_engineering_proposal_client_response(
            released_snapshot=released(),
            response_status="ACCEPTED",
            engineering_user="",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("expected Engineering identity requirement")


def test_acceptance_is_explicit_but_does_not_create_job():
    result=record_property_engineering_proposal_client_response(
        released_snapshot=released(),
        response_status="ACCEPTED",
        engineering_user="engineer@midra.test",
    )
    assert result["client_response_status"]=="ACCEPTED"
    assert result["client_approved"] is True
    assert result["engineering_job_created"] is False
    assert result["property_analysis_engineer_accepted"] is False


def test_decline_is_explicit_and_not_approval():
    result=record_property_engineering_proposal_client_response(
        released_snapshot=released(),
        response_status="DECLINED",
        engineering_user="engineer@midra.test",
    )
    assert result["client_response_status"]=="DECLINED"
    assert result["client_approved"] is False


def test_response_requires_released_proposal():
    bad=released(); bad["sent"]=False
    try:
        record_property_engineering_proposal_client_response(
            released_snapshot=bad,
            response_status="ACCEPTED",
            engineering_user="engineer@midra.test",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected released proposal requirement")
