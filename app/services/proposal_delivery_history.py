"""Phase 5.36 — persistent proposal delivery history/status projection."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable


ALLOWED_DELIVERY_STATUSES = {"SENT", "DELIVERED", "FAILED"}


@dataclass(frozen=True)
class ProposalDeliveryEvent:
    proposal_id: str
    release_id: str
    artifact_id: str
    recipient: str
    pdf_sha256: str
    authorized_by: str
    status: str
    occurred_at: str
    delivery_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def record_delivery_event(
    *,
    proposal_id: str,
    release_id: str,
    artifact_id: str,
    recipient: str,
    pdf_sha256: str,
    authorized_by: str,
    status: str,
    delivery_id: str | None = None,
    occurred_at: str | None = None,
) -> dict:
    """Create an append-only delivery-history event from an already-controlled delivery."""
    if status not in ALLOWED_DELIVERY_STATUSES:
        raise ValueError("unsupported delivery status")
    required = {
        "proposal_id": proposal_id,
        "release_id": release_id,
        "artifact_id": artifact_id,
        "recipient": recipient,
        "pdf_sha256": pdf_sha256,
        "authorized_by": authorized_by,
    }
    if any(not str(value).strip() for value in required.values()):
        raise ValueError("delivery history requires complete delivery identity")
    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    return ProposalDeliveryEvent(
        proposal_id=proposal_id,
        release_id=release_id,
        artifact_id=artifact_id,
        recipient=recipient,
        pdf_sha256=pdf_sha256,
        authorized_by=authorized_by,
        status=status,
        occurred_at=timestamp,
        delivery_id=delivery_id,
    ).to_dict()


def proposal_delivery_history(*, proposal_id: str, events: Iterable[dict]) -> list[dict]:
    """Return one proposal's immutable event history in chronological order."""
    matching = [dict(e) for e in events if e.get("proposal_id") == proposal_id]
    return sorted(matching, key=lambda e: e["occurred_at"])


def proposal_delivery_status(*, proposal_id: str, events: Iterable[dict]) -> dict:
    """Project current delivery status without modifying historical events."""
    history = proposal_delivery_history(proposal_id=proposal_id, events=events)
    if not history:
        return {"proposal_id": proposal_id, "status": "NOT_SENT", "latest_event": None}
    latest = history[-1]
    return {
        "proposal_id": proposal_id,
        "status": latest["status"],
        "latest_event": latest,
    }


def delivery_audit_view(*, event: dict) -> dict:
    """Expose the exact audit fields needed by the private Engineering workspace."""
    keys = (
        "proposal_id", "release_id", "artifact_id", "recipient", "pdf_sha256",
        "authorized_by", "status", "occurred_at", "delivery_id",
    )
    return {key: event.get(key) for key in keys}
