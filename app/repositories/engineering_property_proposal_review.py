"""Durable approval repository for Property-origin MIDRA Engineering proposals."""
from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.services.property_engineering_proposal_lifecycle import validate_property_engineering_proposal_transition


class SQLAlchemyEngineeringPropertyProposalReviewRepository:
    def __init__(self, db: Session):
        self.db=db

    def _draft(
        self, *, property_record_id: str, proposal_request_id: str, engineering_draft_id: str
    ) -> EngineeringPropertyProposalDraft:
        draft=self.db.get(EngineeringPropertyProposalDraft, engineering_draft_id)
        if (
            draft is None
            or draft.property_record_id != property_record_id
            or draft.proposal_request_id != proposal_request_id
        ):
            raise KeyError("engineering_draft")
        return draft

    def get_for_draft(
        self, *, property_record_id: str, proposal_request_id: str, engineering_draft_id: str
    ) -> EngineeringPropertyProposalReview:
        self._draft(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_draft_id=engineering_draft_id,
        )
        stmt=(select(EngineeringPropertyProposalReview)
              .where(EngineeringPropertyProposalReview.engineering_draft_id==engineering_draft_id))
        item=self.db.scalar(stmt)
        if item is None:
            raise KeyError("engineering_review")
        return item

    def list(
        self, *, property_record_id: str, proposal_request_id: str
    ) -> list[EngineeringPropertyProposalReview]:
        stmt=(select(EngineeringPropertyProposalReview)
              .where(
                  EngineeringPropertyProposalReview.property_record_id==property_record_id,
                  EngineeringPropertyProposalReview.proposal_request_id==proposal_request_id,
              )
              .order_by(EngineeringPropertyProposalReview.created_at.desc()))
        return list(self.db.scalars(stmt))

    def create_approval(
        self, *, property_record_id: str, proposal_request_id: str, engineering_draft_id: str,
        approved_snapshot: dict, reviewed_by: str,
    ) -> EngineeringPropertyProposalReview:
        draft=self._draft(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_draft_id=engineering_draft_id,
        )
        existing=self.db.scalar(
            select(EngineeringPropertyProposalReview)
            .where(EngineeringPropertyProposalReview.engineering_draft_id==engineering_draft_id)
        )
        if existing is not None:
            return existing

        actor=str(reviewed_by or "").strip()
        if not actor:
            raise ValueError("reviewed_by is required")
        if approved_snapshot.get("status") != "APPROVED_READY_TO_SEND":
            raise ValueError("only engineer-approved proposal snapshots may enter the review workspace")
        if approved_snapshot.get("send_allowed") is not True or approved_snapshot.get("sent") is True:
            raise ValueError("approved proposal snapshot must be send-eligible and unsent")
        if str(approved_snapshot.get("proposal_id") or "").strip() != draft.proposal_id:
            raise ValueError("approved proposal identity does not match the durable draft")

        request=self.db.get(PropertyEngineeringProposalRequest, proposal_request_id)
        if request is None or request.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        current=str(request.request_status or "").strip().upper()
        if current == "REQUESTED":
            transition=validate_property_engineering_proposal_transition(current, "PROPOSAL_GENERATED")
            if transition.get("transition_permitted") is not True:
                raise ValueError("proposal lifecycle does not permit generated status")
            request.request_status="PROPOSAL_GENERATED"
        elif current != "PROPOSAL_GENERATED":
            raise ValueError("proposal request is not awaiting Engineering proposal generation")

        item=EngineeringPropertyProposalReview(
            engineering_review_id=str(uuid.uuid4()),
            engineering_draft_id=engineering_draft_id,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=draft.proposal_id,
            proposal_number=draft.proposal_number,
            review_status="APPROVED_READY_TO_SEND",
            approved_snapshot=dict(approved_snapshot),
            reviewed_by=actor,
        )
        self.db.add(request)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
