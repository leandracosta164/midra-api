from types import SimpleNamespace

from app.services.property_engineering_proposal_context import build_property_engineering_proposal_context
from app.services.property_engineering_proposal_lifecycle import classify_property_engineering_proposal_lifecycle


def test_requested_status_is_not_job_eligible():
    state = classify_property_engineering_proposal_lifecycle("REQUESTED")
    assert state["state"] == "AWAITING_ENGINEERING_PROPOSAL"
    assert state["proposal_generated"] is False
    assert state["client_approved"] is False
    assert state["job_creation_eligible"] is False
    assert state["next_required_event"] == "ENGINEERING_PROPOSAL_GENERATED"


def test_generated_proposal_still_requires_client_approval():
    state = classify_property_engineering_proposal_lifecycle("PROPOSAL_GENERATED")
    assert state["proposal_generated"] is True
    assert state["client_approved"] is False
    assert state["job_creation_eligible"] is False
    assert state["next_required_event"] == "CLIENT_APPROVAL"


def test_client_approved_status_only_marks_eligibility_for_separate_job_creation():
    state = classify_property_engineering_proposal_lifecycle("CLIENT_APPROVED")
    assert state["proposal_generated"] is True
    assert state["client_approved"] is True
    assert state["job_creation_eligible"] is True
    assert state["state"] == "ELIGIBLE_FOR_SEPARATE_ENGINEERING_JOB_CREATION"
    assert state["next_required_event"] == "AUTHORIZED_ENGINEERING_JOB_CREATION"


def test_unknown_status_is_verify_and_never_job_eligible():
    state = classify_property_engineering_proposal_lifecycle("SOMETHING_NEW")
    assert state["requires_verification"] is True
    assert state["job_creation_eligible"] is False
    assert state["state"] == "VERIFY_UNSUPPORTED_PROPOSAL_STATUS"


def test_context_carries_lifecycle_but_does_not_create_job():
    context = build_property_engineering_proposal_context(
        proposal_request=SimpleNamespace(request_status="CLIENT_APPROVED"),
        property_record=SimpleNamespace(property_record_id="p1"),
        analysis_run=None,
    )
    assert context["proposal_lifecycle"]["job_creation_eligible"] is True
    assert context["engineering_job_created"] is False
    assert context["professional_boundary"]["engineer_reviewed"] is False
    assert context["professional_boundary"]["engineer_accepted"] is False
