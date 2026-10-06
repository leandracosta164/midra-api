"""Schemas for authorized Engineering job creation from Property-origin proposals."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.engineering_job import EngineeringJobRead
from app.schemas.property_record import PropertyEngineeringJobLinkRead


class EngineeringPropertyProposalJobCreationRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    engineering_job_creation_id: str
    engineering_client_response_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    engineering_job_number: str
    creation_snapshot: dict[str, Any]
    created_by: str
    created_at: datetime


class EngineeringPropertyProposalJobCreationActionRead(BaseModel):
    job_creation: EngineeringPropertyProposalJobCreationRead
    engineering_job: EngineeringJobRead
    property_link: PropertyEngineeringJobLinkRead
    proposal_request_status: str
    engineering_job_created: bool
    property_analysis_engineer_accepted: bool
