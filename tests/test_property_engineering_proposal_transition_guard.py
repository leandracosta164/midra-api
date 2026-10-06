from app.services.property_engineering_proposal_lifecycle import (
    allowed_property_engineering_proposal_transitions,
    classify_property_engineering_proposal_lifecycle,
    validate_property_engineering_proposal_transition,
)


def test_requested_allows_only_generation_or_cancel():
    assert allowed_property_engineering_proposal_transitions("REQUESTED") == [
        "PROPOSAL_GENERATED", "CANCELLED"
    ]
    assert validate_property_engineering_proposal_transition(
        "REQUESTED", "PROPOSAL_GENERATED"
    )["transition_permitted"] is True
    assert validate_property_engineering_proposal_transition(
        "REQUESTED", "CLIENT_APPROVED"
    )["transition_permitted"] is False


def test_generated_allows_client_decision_or_cancel():
    assert allowed_property_engineering_proposal_transitions("PROPOSAL_GENERATED") == [
        "CLIENT_APPROVED", "DECLINED", "CANCELLED"
    ]


def test_client_approved_and_closed_states_are_terminal_in_property_workflow():
    assert allowed_property_engineering_proposal_transitions("CLIENT_APPROVED") == []
    assert allowed_property_engineering_proposal_transitions("DECLINED") == []
    assert allowed_property_engineering_proposal_transitions("CANCELLED") == []


def test_unknown_current_status_requires_verification_and_never_allows_transition():
    result = validate_property_engineering_proposal_transition("UNKNOWN", "CLIENT_APPROVED")
    assert result["transition_permitted"] is False
    assert result["requires_verification"] is True
    assert result["reason"] == "VERIFY_UNSUPPORTED_CURRENT_STATUS"


def test_classifier_exposes_allowed_next_statuses_without_mutating_status():
    state = classify_property_engineering_proposal_lifecycle("REQUESTED")
    assert state["status"] == "REQUESTED"
    assert state["allowed_next_statuses"] == ["PROPOSAL_GENERATED", "CANCELLED"]
