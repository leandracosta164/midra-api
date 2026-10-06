"""Atomic durable Engineering job creation from accepted Property-origin proposals."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_job import EngineeringJob
from app.models.engineering_property_proposal_client_response import EngineeringPropertyProposalClientResponse
from app.models.engineering_property_proposal_job_creation import EngineeringPropertyProposalJobCreation
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.property_record import PropertyRecord
from app.services.property_engineering_job_creation_bridge import build_authorized_engineering_job_creation


class SQLAlchemyEngineeringPropertyProposalJobCreationRepository:
    def __init__(self, db: Session):
        self.db=db

    def get_for_proposal(self, *, property_record_id: str, proposal_request_id: str) -> EngineeringPropertyProposalJobCreation:
        item=self.db.scalar(select(EngineeringPropertyProposalJobCreation).where(
            EngineeringPropertyProposalJobCreation.property_record_id==property_record_id,
            EngineeringPropertyProposalJobCreation.proposal_request_id==proposal_request_id,
        ))
        if item is None:
            raise KeyError("engineering_job_creation")
        return item

    def get_for_proposal_optional(self, *, property_record_id: str, proposal_request_id: str) -> EngineeringPropertyProposalJobCreation | None:
        try:
            return self.get_for_proposal(property_record_id=property_record_id,proposal_request_id=proposal_request_id)
        except KeyError:
            return None

    def create_from_accepted_response(
        self,
        *,
        property_record_id: str,
        proposal_request_id: str,
        engineering_client_response_id: str,
        engineering_user: str,
        year: int | None=None,
    ) -> EngineeringPropertyProposalJobCreation:
        existing=self.get_for_proposal_optional(property_record_id=property_record_id,proposal_request_id=proposal_request_id)
        if existing is not None:
            if existing.engineering_client_response_id != engineering_client_response_id:
                raise ValueError("proposal already created an Engineering job from a different client response")
            return existing

        property_record=self.db.get(PropertyRecord,property_record_id)
        if property_record is None:
            raise KeyError("property")
        proposal=self.db.get(PropertyEngineeringProposalRequest,proposal_request_id)
        if proposal is None or proposal.property_record_id != property_record_id:
            raise KeyError("proposal_request")
        response=self.db.get(EngineeringPropertyProposalClientResponse,engineering_client_response_id)
        if response is None or response.property_record_id != property_record_id or response.proposal_request_id != proposal_request_id:
            raise KeyError("engineering_client_response")

        existing_numbers=list(self.db.scalars(select(EngineeringJob.job_number)).all())
        built=build_authorized_engineering_job_creation(
            property_record=property_record,
            proposal_request=proposal,
            client_response=response,
            engineering_user=engineering_user,
            existing_job_numbers=existing_numbers,
            year=year,
        )
        job_values=dict(built["job"])
        job=EngineeringJob(**job_values)
        self.db.add(job)
        self.db.flush()

        now: datetime=job.created_at
        link=PropertyEngineeringJobLink(
            link_id=str(uuid.uuid4()),
            property_record_id=property_record_id,
            engineering_job_number=job.job_number,
            link_status="linked",
            created_by=str(engineering_user or "").strip(),
            notes=f"Created from accepted Property proposal {proposal_request_id}",
            created_at=now,
            updated_at=now,
        )
        audit=EngineeringPropertyProposalJobCreation(
            engineering_job_creation_id=str(uuid.uuid4()),
            engineering_client_response_id=engineering_client_response_id,
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            proposal_id=response.proposal_id,
            proposal_number=response.proposal_number,
            engineering_job_number=job.job_number,
            creation_snapshot=dict(built["creation_snapshot"]),
            created_by=str(engineering_user or "").strip(),
            created_at=now,
        )
        self.db.add(link)
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return audit
