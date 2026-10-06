"""Phase 5.37 — private MIDRA Engineering proposal dashboard projection."""
from __future__ import annotations

DASHBOARD_BUCKETS = (
    "AWAITING_REVIEW",
    "READY_TO_SEND",
    "SENT_OR_DELIVERED",
    "DELIVERY_ATTENTION",
)


def classify_proposal_workflow(*, proposal: dict, delivery_status: str = "NOT_SENT") -> str:
    """Classify a proposal into exactly one Engineering dashboard work queue."""
    status = proposal.get("status")

    if delivery_status == "FAILED":
        return "DELIVERY_ATTENTION"
    if delivery_status in {"SENT", "DELIVERED"}:
        return "SENT_OR_DELIVERED"
    if status == "APPROVED_READY_TO_SEND":
        return "READY_TO_SEND"
    return "AWAITING_REVIEW"


def build_proposal_dashboard(*, proposals: list[dict], delivery_status_by_proposal: dict[str, str]) -> dict:
    """Build a private dashboard projection without changing proposal state."""
    queues = {bucket: [] for bucket in DASHBOARD_BUCKETS}

    for proposal in proposals:
        proposal_id = proposal.get("proposal_id")
        delivery_status = delivery_status_by_proposal.get(proposal_id, "NOT_SENT")
        bucket = classify_proposal_workflow(
            proposal=proposal,
            delivery_status=delivery_status,
        )
        item = {
            "proposal_id": proposal_id,
            "status": proposal.get("status"),
            "delivery_status": delivery_status,
            "client_name": proposal.get("client_name"),
            "property_address": proposal.get("property_address"),
            "project_goal": proposal.get("project_goal"),
            "proposal_number": proposal.get("proposal_number"),
            "proposal_date": proposal.get("proposal_date"),
        }
        queues[bucket].append(item)

    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "queues": queues,
        "counts": {name: len(items) for name, items in queues.items()},
    }


def proposal_dashboard_detail(*, proposal: dict, delivery_history: list[dict]) -> dict:
    """Project the proposal detail needed by the Engineering dashboard."""
    return {
        "proposal_id": proposal.get("proposal_id"),
        "proposal_number": proposal.get("proposal_number"),
        "client_name": proposal.get("client_name"),
        "property_address": proposal.get("property_address"),
        "project_goal": proposal.get("project_goal"),
        "status": proposal.get("status"),
        "delivery_history": [dict(event) for event in delivery_history],
        "available_actions": _available_actions(
            proposal_status=proposal.get("status"),
            delivery_history=delivery_history,
        ),
    }


def _available_actions(*, proposal_status: str | None, delivery_history: list[dict]) -> list[str]:
    latest = delivery_history[-1]["status"] if delivery_history else "NOT_SENT"
    if latest == "FAILED":
        return ["REVIEW_DELIVERY_FAILURE"]
    if latest in {"SENT", "DELIVERED"}:
        return ["VIEW_DELIVERY_HISTORY", "DOWNLOAD_SENT_PDF"]
    if proposal_status == "APPROVED_READY_TO_SEND":
        return ["PREVIEW_APPROVED_PDF", "SEND_PROPOSAL"]
    return ["OPEN_FOR_REVIEW"]
