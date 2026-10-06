from app.services.property_engineering_proposal_lifecycle import classify_property_engineering_proposal_lifecycle


def test_requested_history_classification_stays_ineligible_for_job_creation():
    lifecycle = classify_property_engineering_proposal_lifecycle("REQUESTED")
    assert lifecycle["state"] == "AWAITING_ENGINEERING_PROPOSAL"
    assert lifecycle["job_creation_eligible"] is False
    assert lifecycle["next_required_event"] == "ENGINEERING_PROPOSAL_GENERATED"


def test_generated_history_classification_stays_ineligible_until_client_approval():
    lifecycle = classify_property_engineering_proposal_lifecycle("PROPOSAL_GENERATED")
    assert lifecycle["state"] == "AWAITING_CLIENT_APPROVAL"
    assert lifecycle["job_creation_eligible"] is False
    assert lifecycle["next_required_event"] == "CLIENT_APPROVAL"


def test_client_approved_history_classification_only_marks_separate_job_eligibility():
    lifecycle = classify_property_engineering_proposal_lifecycle("CLIENT_APPROVED")
    assert lifecycle["state"] == "ELIGIBLE_FOR_SEPARATE_ENGINEERING_JOB_CREATION"
    assert lifecycle["job_creation_eligible"] is True
    assert lifecycle["next_required_event"] == "AUTHORIZED_ENGINEERING_JOB_CREATION"


def test_unknown_history_status_remains_verify_and_ineligible():
    lifecycle = classify_property_engineering_proposal_lifecycle("UNRECOGNIZED")
    assert lifecycle["state"] == "VERIFY_UNSUPPORTED_PROPOSAL_STATUS"
    assert lifecycle["requires_verification"] is True
    assert lifecycle["job_creation_eligible"] is False
