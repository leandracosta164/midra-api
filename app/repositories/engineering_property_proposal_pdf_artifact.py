"""SQLAlchemy durable store for immutable Property-origin Engineering proposal PDFs."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_pdf_artifact import EngineeringPropertyProposalPdfArtifact


def _text(value) -> str:
    return str(value or "").strip()


class SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, artifact_id: str) -> EngineeringPropertyProposalPdfArtifact | None:
        return self.db.get(EngineeringPropertyProposalPdfArtifact, _text(artifact_id))

    def get_for_release(self, engineering_release_id: str) -> EngineeringPropertyProposalPdfArtifact | None:
        return self.db.scalar(
            select(EngineeringPropertyProposalPdfArtifact).where(
                EngineeringPropertyProposalPdfArtifact.engineering_release_id == _text(engineering_release_id)
            )
        )

    def create_from_record(
        self,
        *,
        engineering_release_id: str,
        property_record_id: str,
        proposal_request_id: str,
        proposal_id: str,
        created_by: str,
        record: dict,
    ) -> EngineeringPropertyProposalPdfArtifact:
        existing = self.get_for_release(engineering_release_id)
        if existing is not None:
            return existing

        actor = _text(created_by)
        data = record.get("pdf_bytes")
        expected_hash = _text(record.get("pdf_sha256"))
        if not actor:
            raise PermissionError("authenticated Engineering user identity is required")
        if record.get("artifact_type") != "MIDRA_ENGINEERING_STORED_PROPOSAL_PDF":
            raise ValueError("durable proposal artifact requires a verified stored PDF record")
        if record.get("immutable") is not True or record.get("retrieval_mode") != "STORED_EXACT_BYTES_NO_RERENDER":
            raise ValueError("proposal PDF artifact must be immutable exact bytes")
        if not isinstance(data, bytes) or not expected_hash or sha256(data).hexdigest() != expected_hash:
            raise ValueError("proposal PDF artifact failed integrity verification")

        snapshot = deepcopy(record)
        snapshot.pop("pdf_bytes", None)
        item = EngineeringPropertyProposalPdfArtifact(
            artifact_id=_text(record.get("artifact_id")),
            engineering_release_id=_text(engineering_release_id),
            property_record_id=_text(property_record_id),
            proposal_request_id=_text(proposal_request_id),
            proposal_id=_text(proposal_id),
            proposal_number=_text(record.get("proposal_number")),
            filename=_text(record.get("filename")),
            mime_type=_text(record.get("mime_type")) or "application/pdf",
            pdf_sha256=expected_hash,
            byte_size=len(data),
            pdf_bytes=bytes(data),
            artifact_snapshot=snapshot,
            created_by=actor,
        )
        if not all((item.artifact_id, item.engineering_release_id, item.property_record_id,
                    item.proposal_request_id, item.proposal_id, item.proposal_number, item.filename)):
            raise ValueError("durable proposal PDF identity is incomplete")
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def exact_bytes(item: EngineeringPropertyProposalPdfArtifact) -> bytes:
        data = bytes(item.pdf_bytes or b"")
        if not data or sha256(data).hexdigest() != _text(item.pdf_sha256):
            raise ValueError("durable proposal PDF failed integrity verification")
        return data
