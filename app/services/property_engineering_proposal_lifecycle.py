"""Conservative lifecycle semantics for Property -> Engineering proposal requests."""
from __future__ import annotations

from typing import Any


_ALLOWED_TRANSITIONS = {
    "REQUESTED": ("PROPOSAL_GENERATED", "CANCELLED"),
    "PROPOSAL_GENERATED": ("CLIENT_APPROVED", "DECLINED", "CANCELLED"),
    "CLIENT_APPROVED": (),
    "CANCELLED": (),
    "DECLINED": (),
}


def allowed_property_engineering_proposal_transitions(request_status: Any) -> list[str]:
    status = str(request_status or "").strip().upper() or "REQUESTED"
    allowed = _ALLOWED_TRANSITIONS.get(status)
    return list(allowed) if allowed is not None else []


def validate_property_engineering_proposal_transition(
    current_status: Any,
    next_status: Any,
) -> dict[str, Any]:
    current = str(current_status or "").strip().upper() or "REQUESTED"
    target = str(next_status or "").strip().upper()
    allowed = allowed_property_engineering_proposal_transitions(current)
    supported_current = current in _ALLOWED_TRANSITIONS
    permitted = bool(target) and supported_current and target in allowed
    return {
        "current_status": current,
        "requested_next_status": target or None,
        "allowed_next_statuses": allowed,
        "transition_permitted": permitted,
        "requires_verification": not supported_current,
        "reason": (
            "TRANSITION_ALLOWED"
            if permitted
            else "VERIFY_UNSUPPORTED_CURRENT_STATUS"
            if not supported_current
            else "TRANSITION_NOT_ALLOWED"
        ),
    }


def classify_property_engineering_proposal_lifecycle(request_status: Any) -> dict[str, Any]:
    status = str(request_status or "").strip().upper() or "REQUESTED"

    if status == "REQUESTED":
        return {
            "status": status,
            "state": "AWAITING_ENGINEERING_PROPOSAL",
            "proposal_generated": False,
            "client_approved": False,
            "job_creation_eligible": False,
            "requires_verification": False,
            "next_required_event": "ENGINEERING_PROPOSAL_GENERATED",
            "allowed_next_statuses": allowed_property_engineering_proposal_transitions(status),
        }

    if status == "PROPOSAL_GENERATED":
        return {
            "status": status,
            "state": "AWAITING_CLIENT_APPROVAL",
            "proposal_generated": True,
            "client_approved": False,
            "job_creation_eligible": False,
            "requires_verification": False,
            "next_required_event": "CLIENT_APPROVAL",
            "allowed_next_statuses": allowed_property_engineering_proposal_transitions(status),
        }

    if status == "CLIENT_APPROVED":
        return {
            "status": status,
            "state": "ELIGIBLE_FOR_SEPARATE_ENGINEERING_JOB_CREATION",
            "proposal_generated": True,
            "client_approved": True,
            "job_creation_eligible": True,
            "requires_verification": False,
            "next_required_event": "AUTHORIZED_ENGINEERING_JOB_CREATION",
            "allowed_next_statuses": allowed_property_engineering_proposal_transitions(status),
        }

    if status in {"CANCELLED", "DECLINED"}:
        return {
            "status": status,
            "state": "CLOSED_NO_JOB",
            "proposal_generated": status == "DECLINED",
            "client_approved": False,
            "job_creation_eligible": False,
            "requires_verification": False,
            "next_required_event": None,
            "allowed_next_statuses": allowed_property_engineering_proposal_transitions(status),
        }

    return {
        "status": status,
        "state": "VERIFY_UNSUPPORTED_PROPOSAL_STATUS",
        "proposal_generated": False,
        "client_approved": False,
        "job_creation_eligible": False,
        "requires_verification": True,
        "next_required_event": "VERIFY_PROPOSAL_STATUS",
        "allowed_next_statuses": [],
    }
