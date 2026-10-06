import pytest
from app.services.proposal_client_response import (
    record_client_proposal_response,
    proposal_response_status,
    proposal_response_history,
    engineering_transition_eligibility,
)

DELIVERY = {
    "proposal_id": "P-1",
    "release_id": "R-1",
    "artifact_id": "PDF-1",
    "pdf_sha256": "a"*64,
    "recipient": "client@example.com",
    "status": "DELIVERED",
    "delivery_id": "D-1",
}

def _record(response="ACCEPTED", **changes):
    args = dict(
        proposal_id="P-1", release_id="R-1", artifact_id="PDF-1",
        pdf_sha256="a"*64, recipient="client@example.com",
        response=response, responded_at="2026-09-18T12:00:00+00:00",
        delivery_record=DELIVERY,
    )
    args.update(changes)
    return record_client_proposal_response(**args)

def test_no_response_is_pending():
    assert proposal_response_status(proposal_id="P-1", responses=[])["status"] == "PENDING"

def test_acceptance_is_bound_to_exact_delivered_artifact():
    r = _record()
    assert r["artifact_id"] == "PDF-1"
    assert r["pdf_sha256"] == "a"*64
    assert r["delivery_id"] == "D-1"

def test_decline_is_recorded_without_destroying_delivery_identity():
    r = _record("DECLINED")
    assert r["response"] == "DECLINED" and r["proposal_id"] == "P-1"

def test_unsent_proposal_cannot_be_accepted():
    bad = dict(DELIVERY); bad["status"] = "NOT_SENT"
    with pytest.raises(ValueError):
        _record(delivery_record=bad)

def test_different_or_outdated_artifact_cannot_be_accepted():
    with pytest.raises(ValueError):
        _record(artifact_id="PDF-OLD")

def test_response_history_is_chronological_and_proposal_scoped():
    first = _record("DECLINED", responded_at="2026-09-18T10:00:00+00:00")
    second = _record("ACCEPTED", responded_at="2026-09-18T11:00:00+00:00")
    other = dict(second); other["proposal_id"] = "P-2"
    h = proposal_response_history(proposal_id="P-1", responses=[second, other, first])
    assert [x["response"] for x in h] == ["DECLINED", "ACCEPTED"]

def test_latest_response_projects_dashboard_status():
    first = _record("DECLINED", responded_at="2026-09-18T10:00:00+00:00")
    second = _record("ACCEPTED", responded_at="2026-09-18T11:00:00+00:00")
    assert proposal_response_status(proposal_id="P-1", responses=[first, second])["status"] == "ACCEPTED"

def test_acceptance_only_makes_project_transition_eligible_not_automatic():
    r = _record()
    result = engineering_transition_eligibility(response_record=r)
    assert result["eligible"] is True
    assert result["action"] == "CREATE_ENGINEERING_PROJECT_REQUIRES_AUTHORIZED_ACTION"
