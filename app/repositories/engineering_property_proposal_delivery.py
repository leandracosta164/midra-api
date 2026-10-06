"""Durable append-only delivery ledger for Property-origin Engineering proposals."""
from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_delivery import EngineeringPropertyProposalDelivery
from app.models.engineering_property_proposal_pdf_artifact import EngineeringPropertyProposalPdfArtifact


class SQLAlchemyEngineeringPropertyProposalDeliveryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, *, property_record_id: str, proposal_request_id: str, engineering_release_id: str | None = None):
        stmt = select(EngineeringPropertyProposalDelivery).where(
            EngineeringPropertyProposalDelivery.property_record_id == property_record_id,
            EngineeringPropertyProposalDelivery.proposal_request_id == proposal_request_id,
        )
        if engineering_release_id:
            stmt = stmt.where(EngineeringPropertyProposalDelivery.engineering_release_id == engineering_release_id)
        return list(self.db.scalars(stmt.order_by(EngineeringPropertyProposalDelivery.created_at.desc())))

    def create_sent(self, *, artifact: EngineeringPropertyProposalPdfArtifact, authorized_by: str, delivery: dict):
        actor = str(authorized_by or "").strip()
        if not actor:
            raise ValueError("authorized_by is required")
        if delivery.get("status") != "SENT" or delivery.get("automatic_send") is not False:
            raise ValueError("only explicit completed proposal deliveries may be recorded")
        if str(delivery.get("artifact_id") or "").strip() != artifact.artifact_id:
            raise ValueError("delivery artifact identity mismatch")
        expected_release_id = str((artifact.artifact_snapshot or {}).get("release_id") or artifact.engineering_release_id).strip()
        if str(delivery.get("release_id") or "").strip() != expected_release_id:
            raise ValueError("delivery release identity mismatch")
        if str(delivery.get("pdf_sha256") or "").strip() != artifact.pdf_sha256:
            raise ValueError("delivery PDF hash mismatch")
        provider_message_id = str(delivery.get("provider_message_id") or "").strip()
        recipient = str(delivery.get("recipient") or "").strip().lower()
        if not provider_message_id or not recipient:
            raise ValueError("delivery confirmation is incomplete")
        item = EngineeringPropertyProposalDelivery(
            engineering_delivery_id=str(uuid.uuid4()),
            engineering_release_id=artifact.engineering_release_id,
            artifact_id=artifact.artifact_id,
            property_record_id=artifact.property_record_id,
            proposal_request_id=artifact.proposal_request_id,
            proposal_id=artifact.proposal_id,
            proposal_number=artifact.proposal_number,
            recipient=recipient,
            delivery_status="SENT",
            provider_message_id=provider_message_id,
            pdf_sha256=artifact.pdf_sha256,
            delivery_snapshot=dict(delivery),
            authorized_by=actor,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
