"""Durable client-release repository for approved Property-origin Engineering proposals."""
from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest


class SQLAlchemyEngineeringPropertyProposalReleaseRepository:
    def __init__(self, db: Session):
        self.db=db

    def _review(
        self, *, property_record_id: str, proposal_request_id: str, engineering_review_id: str
    ) -> EngineeringPropertyProposalReview:
        review=self.db.get(EngineeringPropertyProposalReview, engineering_review_id)
        if (
            review is None
            or review.property_record_id != property_record_id
            or review.proposal_request_id != proposal_request_id
        ):
            raise KeyError("engineering_review")
        return review

    def get_for_review(
        self, *, property_record_id: str, proposal_request_id: str, engineering_review_id: str
    ) -> EngineeringPropertyProposalRelease:
        self._review(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_review_id=engineering_review_id,
        )
        item=self.db.scalar(
            select(EngineeringPropertyProposalRelease)
            .where(EngineeringPropertyProposalRelease.engineering_review_id==engineering_review_id)
        )
        if item is None:
            raise KeyError("engineering_release")
        return item

    def list(
        self, *, property_record_id: str, proposal_request_id: str
    ) -> list[EngineeringPropertyProposalRelease]:
        stmt=(select(EngineeringPropertyProposalRelease)
              .where(
                  EngineeringPropertyProposalRelease.property_record_id==property_record_id,
                  EngineeringPropertyProposalRelease.proposal_request_id==proposal_request_id,
              )
              .order_by(EngineeringPropertyProposalRelease.created_at.desc()))
        return list(self.db.scalars(stmt))

    def create_release(
        self, *, property_record_id: str, proposal_request_id: str, engineering_review_id: str,
        released_snapshot: dict, released_by: str,
    ) -> EngineeringPropertyProposalRelease:
        review=self._review(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_review_id=engineering_review_id,
        )
        existing=self.db.scalar(
            select(EngineeringPropertyProposalRelease)
            .where(EngineeringPropertyProposalRelease.engineering_review_id==engineering_review_id)
        )
        if existing is not None:
            return existing

        actor=str(released_by or "").strip()
        if not actor:
            raise ValueError("released_by is required")
        if review.review_status != "APPROVED_READY_TO_SEND":
            raise ValueError("proposal must be engineer-approved before client release")
        if released_snapshot.get("status") != "SENT" or released_snapshot.get("sent") is not True:
            raise ValueError("released proposal snapshot must record a completed send/release action")
        if str(released_snapshot.get("proposal_id") or "").strip() != review.proposal_id:
            raise ValueError("released proposal identity does not match the approved review")

        request=self.db.get(PropertyEngineeringProposalRequest, proposal_request_id)
        if request is None or request.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        if str(request.request_status or "").strip().upper() != "PROPOSAL_GENERATED":
            raise ValueError("proposal request is not awaiting client response")

        item=EngineeringPropertyProposalRelease(
            engineering_release_id=str(uuid.uuid4()),
            engineering_review_id=engineering_review_id,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=review.proposal_id,
            proposal_number=review.proposal_number,
            release_status="SENT_AWAITING_CLIENT_RESPONSE",
            released_snapshot=dict(released_snapshot),
            released_by=actor,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
