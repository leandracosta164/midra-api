from app.services.proposal_dashboard import (
    build_proposal_dashboard,
    classify_proposal_workflow,
    proposal_dashboard_detail,
)


def _proposal(pid, status, **extra):
    return {
        "proposal_id": pid,
        "status": status,
        "client_name": "Client",
        "property_address": "1 Main St",
        "project_goal": "pool",
        "proposal_number": f"P-{pid}",
        "proposal_date": "2026-09-18",
        **extra,
    }


def test_draft_or_review_proposal_is_awaiting_review():
    assert classify_proposal_workflow(proposal=_proposal("1", "DRAFT")) == "AWAITING_REVIEW"


def test_approved_unsent_proposal_is_ready_to_send():
    assert classify_proposal_workflow(
        proposal=_proposal("1", "APPROVED_READY_TO_SEND")
    ) == "READY_TO_SEND"


def test_sent_and_delivered_are_history_not_pending_send():
    for status in ("SENT", "DELIVERED"):
        assert classify_proposal_workflow(
            proposal=_proposal("1", "APPROVED_READY_TO_SEND"),
            delivery_status=status,
        ) == "SENT_OR_DELIVERED"


def test_failed_delivery_gets_attention_even_if_proposal_is_approved():
    assert classify_proposal_workflow(
        proposal=_proposal("1", "APPROVED_READY_TO_SEND"),
        delivery_status="FAILED",
    ) == "DELIVERY_ATTENTION"


def test_dashboard_counts_and_queues_are_consistent():
    proposals = [
        _proposal("1", "DRAFT"),
        _proposal("2", "APPROVED_READY_TO_SEND"),
        _proposal("3", "APPROVED_READY_TO_SEND"),
        _proposal("4", "APPROVED_READY_TO_SEND"),
    ]
    result = build_proposal_dashboard(
        proposals=proposals,
        delivery_status_by_proposal={"3": "DELIVERED", "4": "FAILED"},
    )
    assert result["counts"] == {
        "AWAITING_REVIEW": 1,
        "READY_TO_SEND": 1,
        "SENT_OR_DELIVERED": 1,
        "DELIVERY_ATTENTION": 1,
    }


def test_dashboard_is_explicitly_private_to_midra_engineering():
    result = build_proposal_dashboard(proposals=[], delivery_status_by_proposal={})
    assert result["visibility"] == "MIDRA_ENGINEERING_PRIVATE"


def test_ready_to_send_detail_requires_explicit_send_action():
    detail = proposal_dashboard_detail(
        proposal=_proposal("2", "APPROVED_READY_TO_SEND"),
        delivery_history=[],
    )
    assert detail["available_actions"] == ["PREVIEW_APPROVED_PDF", "SEND_PROPOSAL"]


def test_sent_detail_exposes_history_and_download_not_send():
    event = {"status": "DELIVERED", "delivery_id": "D-1"}
    detail = proposal_dashboard_detail(
        proposal=_proposal("3", "APPROVED_READY_TO_SEND"),
        delivery_history=[event],
    )
    assert "SEND_PROPOSAL" not in detail["available_actions"]
    assert detail["available_actions"] == ["VIEW_DELIVERY_HISTORY", "DOWNLOAD_SENT_PDF"]
