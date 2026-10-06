from app.services.engineering_proposal_client_portal import create_client_proposal_token, verify_client_proposal_token


def args():
    return dict(property_record_id="prop-1",proposal_request_id="req-1",engineering_release_id="rel-1",recipient="client@example.com")


def test_signed_response_token_round_trip_and_identity():
    secret="this-is-a-long-test-secret-for-midra"
    token=create_client_proposal_token(secret=secret,now=1000,ttl_seconds=60,**args())
    payload=verify_client_proposal_token(token=token,secret=secret,now=1050,**args())
    assert payload["engineering_release_id"]=="rel-1"
    assert payload["recipient"]=="client@example.com"


def test_signed_response_token_rejects_tamper_identity_and_expiry():
    secret="this-is-a-long-test-secret-for-midra"
    token=create_client_proposal_token(secret=secret,now=1000,ttl_seconds=60,**args())
    try:
        verify_client_proposal_token(token=token+"x",secret=secret,now=1050,**args())
        assert False
    except ValueError:
        pass
    try:
        verify_client_proposal_token(token=token,secret=secret,now=1050,**(args()|{"engineering_release_id":"other"}))
        assert False
    except ValueError:
        pass
    try:
        verify_client_proposal_token(token=token,secret=secret,now=1061,**args())
        assert False
    except ValueError:
        pass
