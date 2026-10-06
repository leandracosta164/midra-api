"""Repository for durable MIDRA Engineering proposal-draft snapshots."""
from __future__ import annotations

import uuid
from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest


class SQLAlchemyEngineeringPropertyProposalDraftRepository:
    def __init__(self, db: Session):
        self.db = db

    def _proposal_request(
        self, property_record_id: str, proposal_request_id: str
    ) -> PropertyEngineeringProposalRequest:
        item = self.db.get(PropertyEngineeringProposalRequest, proposal_request_id)
        if item is None or item.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        return item

    def create(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        draft_snapshot: dict,
        generated_by: str,
    ) -> EngineeringPropertyProposalDraft:
        self._proposal_request(property_record_id, proposal_request_id)
        snapshot = deepcopy(draft_snapshot or {})
        proposal_id = str(snapshot.get("proposal_id") or "").strip()
        proposal_number = str(snapshot.get("proposal_number") or "").strip()
        proposal_status = str(snapshot.get("status") or "").strip()
        actor = str(generated_by or "").strip()
        if not proposal_id or not proposal_number:
            raise ValueError("proposal_id and proposal_number are required")
        if proposal_status != "DRAFT_REQUIRES_ENGINEER_REVIEW":
            raise ValueError("only review-required proposal drafts may be persisted")
        if not actor:
            raise ValueError("generated_by is required")

        item = EngineeringPropertyProposalDraft(
            engineering_draft_id=str(uuid.uuid4()),
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=proposal_id,
            proposal_number=proposal_number,
            proposal_status=proposal_status,
            draft_snapshot=snapshot,
            generated_by=actor,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        engineering_draft_id: str,
    ) -> EngineeringPropertyProposalDraft:
        self._proposal_request(property_record_id, proposal_request_id)
        item = self.db.get(EngineeringPropertyProposalDraft, engineering_draft_id)
        if (
            item is None
            or item.property_record_id != property_record_id
            or item.proposal_request_id != proposal_request_id
        ):
            raise KeyError("engineering_draft")
        return item

    def list(
        self, *, property_record_id: str, proposal_request_id: str
    ) -> list[EngineeringPropertyProposalDraft]:
        self._proposal_request(property_record_id, proposal_request_id)
        stmt = (
            select(EngineeringPropertyProposalDraft)
            .where(
                EngineeringPropertyProposalDraft.property_record_id == property_record_id,
                EngineeringPropertyProposalDraft.proposal_request_id == proposal_request_id,
            )
            .order_by(EngineeringPropertyProposalDraft.created_at.desc())
        )
        return list(self.db.scalars(stmt))
