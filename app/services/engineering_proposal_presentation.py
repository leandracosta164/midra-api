"""Client-safe presentation contract for MIDRA Engineering proposals.

Phase 5.30 deliberately does not send proposals or own pricing.  It converts an
already reviewed/frozen engineering proposal snapshot into a render-ready,
client-facing document model while preventing private pricing metadata and
MIDRA Intelligence internals from leaking into the document.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

ALLOWED_STATUSES = {"DRAFT", "APPROVED_READY_TO_SEND", "SENT"}


def _money(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("service price must be numeric")
    if value < 0:
        raise ValueError("service price cannot be negative")
    return f"${value:,.2f}"


def build_client_proposal_document_model(*, proposal: dict[str, Any]) -> dict[str, Any]:
    """Build the client-visible MIDRA Engineering proposal presentation model.

    The input is expected to be a proposal snapshot owned by MIDRA Engineering.
    Private library metadata, standard/base prices, override history, analysis
    internals, and evidence records are intentionally excluded.
    """
    status = proposal.get("status")
    if status not in ALLOWED_STATUSES:
        raise ValueError("unsupported proposal status")

    services = proposal.get("services") or []
    if not services:
        raise ValueError("proposal must contain at least one service")

    client_services: list[dict[str, str]] = []
    total = 0.0
    for item in services:
        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError("service name is required")
        price = item.get("proposal_price", item.get("price"))
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValueError("service price must be numeric")
        if price < 0:
            raise ValueError("service price cannot be negative")
        total += float(price)
        # No scope descriptions by product decision.
        client_services.append({"service": name, "price": _money(price)})

    stored_total = proposal.get("total_price")
    if stored_total is not None and abs(float(stored_total) - total) > 0.005:
        raise ValueError("proposal total does not match service prices")

    project = deepcopy(proposal.get("project") or {})
    prepared_for = deepcopy(proposal.get("prepared_for") or {})

    return {
        "document_type": "MIDRA_ENGINEERING_PROPOSAL",
        "brand": "MIDRA Engineering",
        "header": {
            "logo_position": "top_left",
            "proposal_number_position": "top_right",
            "date_position": "top_right",
            "title": "PROPOSAL",
            "title_position": "center_below_header",
            "proposal_number": proposal.get("proposal_number"),
            "date": proposal.get("proposal_date"),
        },
        "project": project,
        "prepared_for": prepared_for,
        "scope_of_services": client_services,
        "total": _money(total),
        "exclusions_additional_services": list(proposal.get("exclusions_additional_services") or []),
        "terms": list(proposal.get("terms") or []),
        "acceptance": {
            "heading": "ACCEPT PROPOSAL",
            "client_signature": True,
            "date": True,
        },
        "status": status,
        "delivery": {
            "automatically_sent": False,
            "requires_explicit_send_action": True,
        },
    }


def proposal_is_sendable(*, proposal: dict[str, Any]) -> bool:
    """Only an explicitly approved proposal is eligible for a separate send action."""
    return proposal.get("status") == "APPROVED_READY_TO_SEND"
