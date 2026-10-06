"""Bridge durable Property-origin proposal PDF artifacts into the controlled delivery service."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.models.engineering_property_proposal_pdf_artifact import EngineeringPropertyProposalPdfArtifact
from app.repositories.engineering_property_proposal_pdf_artifact import SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository
from app.services.engineering_proposal_delivery import deliver_stored_proposal_pdf


class DurableProposalPdfStoreAdapter:
    """Read-only ProposalPdfStore adapter over the durable 2.40 SQL artifact."""
    def __init__(self, artifact_repo: SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository):
        self.artifact_repo = artifact_repo

    def put(self, artifact_id: str, record: dict[str, Any]) -> None:
        raise PermissionError("durable proposal PDF delivery store is read-only")

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        item = self.artifact_repo.get(artifact_id)
        if item is None:
            return None
        data = self.artifact_repo.exact_bytes(item)
        snapshot = deepcopy(item.artifact_snapshot or {})
        return {
            "artifact_type": "MIDRA_ENGINEERING_STORED_PROPOSAL_PDF",
            "artifact_id": item.artifact_id,
            "release_id": snapshot.get("release_id") or item.engineering_release_id,
            "proposal_number": item.proposal_number,
            "filename": item.filename,
            "mime_type": item.mime_type,
            "pdf_sha256": item.pdf_sha256,
            "byte_size": item.byte_size,
            "pdf_bytes": data,
            "persisted_at": snapshot.get("persisted_at"),
            "immutable": True,
            "retrieval_mode": "STORED_EXACT_BYTES_NO_RERENDER",
            "transport": {
                "sent": False,
                "automatic_send": False,
                "requires_separate_authorized_send_action": True,
            },
        }


def deliver_durable_property_proposal_pdf(
    *, artifact: EngineeringPropertyProposalPdfArtifact, recipient: str, authorized_by: str,
    explicit_send_authorized: bool, artifact_repo: SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository,
    transport,
) -> dict[str, Any]:
    if artifact.artifact_id != str(artifact.artifact_id or "").strip():
        raise ValueError("durable proposal PDF artifact identity is invalid")
    return deliver_stored_proposal_pdf(
        artifact_id=artifact.artifact_id,
        recipient=recipient,
        authorized_by=authorized_by,
        explicit_send_authorized=explicit_send_authorized,
        store=DurableProposalPdfStoreAdapter(artifact_repo),
        transport=transport,
    )
