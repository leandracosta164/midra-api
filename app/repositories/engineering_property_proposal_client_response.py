"""Durable client-response repository for released Property-origin Engineering proposals."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_property_proposal_client_response import (
    EngineeringPropertyProposalClientResponse,
)
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.services.property_engineering_proposal_lifecycle import (
    validate_property_engineering_proposal_transition,
)


class SQLAlchemyEngineeringPropertyProposalClientResponseRepository:
    def __init__(self, db: Session):
        self.db=db

    def _release(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        engineering_release_id: str,
    ) -> EngineeringPropertyProposalRelease:
        release=self.db.get(EngineeringPropertyProposalRelease, engineering_release_id)
        if (
            release is None
            or release.property_record_id != property_record_id
            or release.proposal_request_id != proposal_request_id
        ):
            raise KeyError("engineering_release")
        return release

    def list(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
    ) -> list[EngineeringPropertyProposalClientResponse]:
        stmt=(
            select(EngineeringPropertyProposalClientResponse)
            .where(
                EngineeringPropertyProposalClientResponse.property_record_id==property_record_id,
                EngineeringPropertyProposalClientResponse.proposal_request_id==proposal_request_id,
            )
            .order_by(EngineeringPropertyProposalClientResponse.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def create_response(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        engineering_release_id: str,
        response_snapshot: dict,
        recorded_by: str,
    ) -> EngineeringPropertyProposalClientResponse:
        release=self._release(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_release_id=engineering_release_id,
        )
        existing=self.db.scalar(
            select(EngineeringPropertyProposalClientResponse)
            .where(
                EngineeringPropertyProposalClientResponse.engineering_release_id
                == engineering_release_id
            )
        )
        if existing is not None:
            return existing

        actor=str(recorded_by or "").strip()
        if not actor:
            raise ValueError("recorded_by is required")
        if release.release_status != "SENT_AWAITING_CLIENT_RESPONSE":
            raise ValueError("proposal release is not awaiting client response")

        response=str(response_snapshot.get("client_response_status") or "").strip().upper()
        if response not in {"ACCEPTED", "DECLINED"}:
            raise ValueError("response snapshot must record ACCEPTED or DECLINED")
        if str(response_snapshot.get("proposal_id") or "").strip() != release.proposal_id:
            raise ValueError("client response proposal identity does not match the release")
        if response_snapshot.get("client_approved") is not (response=="ACCEPTED"):
            raise ValueError("client response approval flag does not match response status")
        if response_snapshot.get("engineering_job_created") is not False:
            raise ValueError("client response must not create an Engineering job")

        request=self.db.get(PropertyEngineeringProposalRequest, proposal_request_id)
        if request is None or request.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        current=str(request.request_status or "").strip().upper()
        if current != "PROPOSAL_GENERATED":
            raise ValueError("proposal request is not awaiting client response")

        next_status="CLIENT_APPROVED" if response=="ACCEPTED" else "DECLINED"
        transition=validate_property_engineering_proposal_transition(current, next_status)
        if transition.get("transition_permitted") is not True:
            raise ValueError("proposal lifecycle does not permit this client response")

        item=EngineeringPropertyProposalClientResponse(
            engineering_client_response_id=str(uuid.uuid4()),
            engineering_release_id=engineering_release_id,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=release.proposal_id,
            proposal_number=release.proposal_number,
            response_status=response,
            response_snapshot=dict(response_snapshot),
            recorded_by=actor,
        )
        request.request_status=next_status
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
