"""Phase 5.38 — proposal acceptance and client response controls."""
from __future__ import annotations

from datetime import datetime, timezone

CLIENT_RESPONSE_STATUSES = {"ACCEPTED", "DECLINED"}


def record_client_proposal_response(
    *,
    proposal_id: str,
    release_id: str,
    artifact_id: str,
    pdf_sha256: str,
    recipient: str,
    response: str,
    responded_at: str | None = None,
    delivery_record: dict,
) -> dict:
    """Bind a client response to the exact proposal artifact that was delivered."""
    if response not in CLIENT_RESPONSE_STATUSES:
        raise ValueError("unsupported client proposal response")

    if delivery_record.get("status") not in {"SENT", "DELIVERED"}:
        raise ValueError("proposal must have been sent before client response")

    identity = {
        "proposal_id": proposal_id,
        "release_id": release_id,
        "artifact_id": artifact_id,
        "pdf_sha256": pdf_sha256,
        "recipient": recipient,
    }
    for key, value in identity.items():
        if not value or delivery_record.get(key) != value:
            raise ValueError(f"client response does not match delivered {key}")

    return {
        **identity,
        "response": response,
        "responded_at": responded_at or datetime.now(timezone.utc).isoformat(),
        "delivery_id": delivery_record.get("delivery_id"),
    }


def proposal_response_status(*, proposal_id: str, responses: list[dict]) -> dict:
    """Project the latest client response while preserving response history separately."""
    matching = [dict(r) for r in responses if r.get("proposal_id") == proposal_id]
    if not matching:
        return {"proposal_id": proposal_id, "status": "PENDING", "latest_response": None}
    matching.sort(key=lambda r: r["responded_at"])
    latest = matching[-1]
    return {
        "proposal_id": proposal_id,
        "status": latest["response"],
        "latest_response": latest,
    }


def proposal_response_history(*, proposal_id: str, responses: list[dict]) -> list[dict]:
    matching = [dict(r) for r in responses if r.get("proposal_id") == proposal_id]
    return sorted(matching, key=lambda r: r["responded_at"])


def engineering_transition_eligibility(*, response_record: dict | None) -> dict:
    """Acceptance permits a future project transition; it does not create one."""
    if not response_record or response_record.get("response") != "ACCEPTED":
        return {"eligible": False, "action": None}
    return {
        "eligible": True,
        "action": "CREATE_ENGINEERING_PROJECT_REQUIRES_AUTHORIZED_ACTION",
        "proposal_id": response_record.get("proposal_id"),
        "release_id": response_record.get("release_id"),
    }
