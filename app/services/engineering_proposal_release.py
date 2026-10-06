"""Phase 5.31 controlled proposal release snapshot for MIDRA Engineering.

Creates an immutable, client-safe release record from an engineer-approved
proposal.  It bridges the private proposal workflow to future PDF/email
transport without performing transport, acceptance, billing, or exposing
MIDRA Intelligence/private pricing metadata.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from app.services.engineering_proposal_presentation import build_client_proposal_document_model


APPROVED_STATUS = "APPROVED_READY_TO_SEND"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _client_input(proposal: dict[str, Any]) -> dict[str, Any]:
    """Adapt private workflow snapshots to the Phase 5.30 client model."""
    scope = proposal.get("services")
    if scope is None:
        scope = proposal.get("scope_of_services") or []
    services = []
    for item in scope:
        raw_price = item.get("proposal_price", item.get("price"))
        try:
            numeric_price = float(raw_price)
        except (TypeError, ValueError):
            numeric_price = raw_price
        services.append({
            "name": item.get("name", item.get("service")),
            "proposal_price": numeric_price,
        })

    project = proposal.get("project")
    if not isinstance(project, dict):
        project = {
            "name": project,
            "address": proposal.get("property_address"),
        }
    prepared_for = proposal.get("prepared_for")
    if not isinstance(prepared_for, dict):
        prepared_for = {"name": prepared_for}

    return {
        "proposal_number": proposal.get("proposal_number"),
        "proposal_date": proposal.get("proposal_date"),
        "status": proposal.get("status"),
        "project": deepcopy(project),
        "prepared_for": deepcopy(prepared_for),
        "services": services,
        "total_price": (float(proposal.get("total_price")) if proposal.get("total_price") is not None else None),
        "exclusions_additional_services": deepcopy(
            proposal.get("exclusions_additional_services", proposal.get("exclusions", [])) or []
        ),
        "terms": deepcopy(proposal.get("terms") or []),
    }


def _fingerprint(document_model: dict[str, Any]) -> str:
    payload = json.dumps(document_model, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def create_proposal_release_snapshot(
    *, proposal: dict[str, Any], released_by: str, released_at: str | None = None
) -> dict[str, Any]:
    """Freeze exactly what is eligible to be presented/sent to the client.

    Release requires prior engineer approval.  It does not send the proposal.
    The returned snapshot contains only the Phase 5.30 client-safe document
    model plus release/audit metadata and a deterministic content fingerprint.
    """
    if proposal.get("status") != APPROVED_STATUS:
        raise ValueError("proposal must be engineer-approved before release")
    if not _text(released_by):
        raise ValueError("released_by is required")

    document = build_client_proposal_document_model(proposal=_client_input(proposal))
    if document.get("status") != APPROVED_STATUS:
        raise ValueError("client document must be approved before release")

    timestamp = released_at or datetime.now(timezone.utc).isoformat()
    fingerprint = _fingerprint(document)
    proposal_number = _text(document.get("header", {}).get("proposal_number"))
    if not proposal_number:
        raise ValueError("proposal number is required")

    return {
        "release_type": "MIDRA_ENGINEERING_PROPOSAL_RELEASE",
        "proposal_number": proposal_number,
        "release_id": "MER-" + fingerprint[:16].upper(),
        "released_by": _text(released_by),
        "released_at": timestamp,
        "content_sha256": fingerprint,
        "document_model": deepcopy(document),
        "immutable_snapshot": True,
        "transport": {
            "sent": False,
            "automatic_send": False,
            "requires_separate_authorized_send_action": True,
        },
    }


def verify_proposal_release_snapshot(*, release: dict[str, Any]) -> bool:
    """Verify that a release's client-visible content has not been modified."""
    document = release.get("document_model")
    expected = _text(release.get("content_sha256"))
    if not isinstance(document, dict) or not expected:
        return False
    return _fingerprint(document) == expected


def mark_release_sent(*, release: dict[str, Any], sent_by: str, sent_at: str | None = None) -> dict[str, Any]:
    """Record a separate send event against an intact release snapshot.

    Actual email/transport integration remains outside Phase 5.31.
    """
    if not verify_proposal_release_snapshot(release=release):
        raise ValueError("proposal release snapshot failed integrity verification")
    if not _text(sent_by):
        raise ValueError("sent_by is required")
    if release.get("transport", {}).get("sent") is True:
        raise ValueError("proposal release is already marked sent")

    result = deepcopy(release)
    result["transport"] = {
        "sent": True,
        "automatic_send": False,
        "requires_separate_authorized_send_action": False,
        "sent_by": _text(sent_by),
        "sent_at": sent_at or datetime.now(timezone.utc).isoformat(),
    }
    return result
