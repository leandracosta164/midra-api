"""Phase 5.35 controlled delivery contract for MIDRA Engineering proposals.

Delivery is allowed only for the exact immutable PDF persisted by Phase 5.34.
The caller must provide an explicit authorized send action and a valid client
recipient. A delivery adapter performs transport; this service records the
artifact hash/identity that was actually dispatched and never re-renders PDFs.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Any, Protocol

from app.services.engineering_proposal_pdf_repository import ProposalPdfStore, retrieve_proposal_pdf

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _text(value: Any) -> str:
    return str(value or "").strip()


class ProposalDeliveryTransport(Protocol):
    def send(self, *, recipient: str, subject: str, filename: str, mime_type: str, content: bytes) -> dict[str, Any]: ...


class InMemoryProposalDeliveryTransport:
    """Test/development adapter; production may later use an approved email provider."""
    def __init__(self) -> None:
        self.deliveries: list[dict[str, Any]] = []

    def send(self, *, recipient: str, subject: str, filename: str, mime_type: str, content: bytes) -> dict[str, Any]:
        item = {
            "recipient": recipient, "subject": subject, "filename": filename,
            "mime_type": mime_type, "content": bytes(content),
            "provider_message_id": f"TEST-{len(self.deliveries)+1:06d}",
        }
        self.deliveries.append(deepcopy(item))
        return deepcopy(item)


def deliver_stored_proposal_pdf(
    *, artifact_id: str, recipient: str, authorized_by: str,
    explicit_send_authorized: bool, store: ProposalPdfStore,
    transport: ProposalDeliveryTransport, sent_at: str | None = None,
) -> dict[str, Any]:
    """Send one exact stored proposal PDF after explicit human-authorized action."""
    if explicit_send_authorized is not True:
        raise PermissionError("explicit authorized send action is required")
    sender = _text(authorized_by)
    if not sender:
        raise PermissionError("authorized sender identity is required")
    email = _text(recipient).lower()
    if not _EMAIL_RE.fullmatch(email):
        raise ValueError("valid client recipient email is required")

    stored = retrieve_proposal_pdf(artifact_id=_text(artifact_id), store=store)
    if stored.get("artifact_type") != "MIDRA_ENGINEERING_STORED_PROPOSAL_PDF" or stored.get("immutable") is not True:
        raise ValueError("delivery requires an immutable stored proposal PDF")
    data = stored.get("pdf_bytes")
    expected_hash = _text(stored.get("pdf_sha256"))
    if not isinstance(data, bytes) or sha256(data).hexdigest() != expected_hash:
        raise ValueError("stored proposal PDF failed delivery integrity verification")

    proposal_number = _text(stored.get("proposal_number"))
    result = transport.send(
        recipient=email,
        subject=f"MIDRA Engineering Proposal {proposal_number}",
        filename=_text(stored.get("filename")),
        mime_type="application/pdf",
        content=bytes(data),
    )
    provider_message_id = _text((result or {}).get("provider_message_id"))
    if not provider_message_id:
        raise RuntimeError("proposal delivery transport did not confirm dispatch")

    return {
        "delivery_type": "MIDRA_ENGINEERING_PROPOSAL_DELIVERY",
        "status": "SENT",
        "artifact_id": stored["artifact_id"],
        "release_id": stored["release_id"],
        "proposal_number": proposal_number,
        "pdf_sha256": expected_hash,
        "filename": stored["filename"],
        "recipient": email,
        "authorized_by": sender,
        "explicit_send_authorized": True,
        "sent_at": sent_at or datetime.now(timezone.utc).isoformat(),
        "provider_message_id": provider_message_id,
        "source": "STORED_EXACT_BYTES_NO_RERENDER",
        "automatic_send": False,
    }
