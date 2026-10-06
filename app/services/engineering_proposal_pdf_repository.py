"""Phase 5.34 persistence/retrieval contract for approved proposal PDFs.

Stores the exact Phase 5.33 PDF bytes as an immutable artifact record linked to
its release/proposal identity. Retrieval returns those stored bytes; it never
silently re-renders a proposal. This service is storage-backend agnostic so a
DB/object-store adapter can replace the in-memory adapter later without changing
artifact semantics.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol

from app.services.engineering_proposal_pdf_renderer import verify_rendered_proposal_pdf


def _text(value: Any) -> str:
    return str(value or "").strip()


class ProposalPdfStore(Protocol):
    def put(self, artifact_id: str, record: dict[str, Any]) -> None: ...
    def get(self, artifact_id: str) -> dict[str, Any] | None: ...


class InMemoryProposalPdfStore:
    """Test/development adapter. Production can use durable DB/object storage."""
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def put(self, artifact_id: str, record: dict[str, Any]) -> None:
        if artifact_id in self._records:
            raise ValueError("proposal PDF artifact already exists and is immutable")
        self._records[artifact_id] = deepcopy(record)

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        record = self._records.get(artifact_id)
        return deepcopy(record) if record is not None else None


def persist_rendered_proposal_pdf(
    *, rendered: dict[str, Any], store: ProposalPdfStore, persisted_at: str | None = None
) -> dict[str, Any]:
    """Persist the exact verified PDF bytes without sending or regenerating them."""
    if not verify_rendered_proposal_pdf(rendered=rendered):
        raise ValueError("rendered proposal PDF failed integrity verification")
    if rendered.get("render_type") != "MIDRA_ENGINEERING_PROPOSAL_PDF_BINARY":
        raise ValueError("unsupported rendered proposal type")
    if rendered.get("client_safe") is not True:
        raise ValueError("only client-safe proposal PDFs may be persisted")
    if rendered.get("transport", {}).get("sent") is True:
        raise ValueError("persistence does not accept an already-sent transport mutation")

    release_id = _text(rendered.get("release_id"))
    proposal_number = _text(rendered.get("proposal_number"))
    filename = _text(rendered.get("filename"))
    pdf_sha = _text(rendered.get("pdf_sha256"))
    pdf_bytes = rendered.get("pdf_bytes")
    if not all((release_id, proposal_number, filename, pdf_sha)) or not isinstance(pdf_bytes, bytes):
        raise ValueError("rendered proposal PDF identity is incomplete")

    artifact_id = "MEPDF-" + pdf_sha[:20].upper()
    record = {
        "artifact_type": "MIDRA_ENGINEERING_STORED_PROPOSAL_PDF",
        "artifact_id": artifact_id,
        "release_id": release_id,
        "proposal_number": proposal_number,
        "filename": filename,
        "mime_type": "application/pdf",
        "pdf_sha256": pdf_sha,
        "byte_size": len(pdf_bytes),
        "pdf_bytes": bytes(pdf_bytes),
        "persisted_at": persisted_at or datetime.now(timezone.utc).isoformat(),
        "immutable": True,
        "retrieval_mode": "STORED_EXACT_BYTES_NO_RERENDER",
        "transport": {
            "sent": False,
            "automatic_send": False,
            "requires_separate_authorized_send_action": True,
        },
    }
    store.put(artifact_id, record)
    return deepcopy(record)


def retrieve_proposal_pdf(*, artifact_id: str, store: ProposalPdfStore) -> dict[str, Any]:
    """Retrieve and integrity-check the exact stored PDF artifact."""
    record = store.get(_text(artifact_id))
    if record is None:
        raise KeyError("proposal PDF artifact not found")
    data = record.get("pdf_bytes")
    expected = _text(record.get("pdf_sha256"))
    if not isinstance(data, bytes) or not expected or sha256(data).hexdigest() != expected:
        raise ValueError("stored proposal PDF failed integrity verification")
    if record.get("immutable") is not True or record.get("retrieval_mode") != "STORED_EXACT_BYTES_NO_RERENDER":
        raise ValueError("stored proposal PDF persistence contract violated")
    return deepcopy(record)
