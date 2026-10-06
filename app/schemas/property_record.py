from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PropertyRecordUpsert(BaseModel):
    search_query: str = Field(min_length=3, max_length=500)
    analysis: dict[str, Any]


class PropertyRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    property_record_id: str
    canonical_key: str
    search_query: str
    display_address: str
    municipality: str | None
    county: str | None
    block: str | None
    lot: str | None
    latitude: float | None
    longitude: float | None
    intelligence_status: str
    latest_analysis: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PropertyAnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_run_id: str
    property_record_id: str
    requested_work: str | None
    intelligence_status: str
    analysis: dict[str, Any]
    created_at: datetime


class PropertyEngineeringJobLinkCreate(BaseModel):
    engineering_job_number: str = Field(min_length=1, max_length=50)
    created_by: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class PropertyEngineeringJobLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    link_id: str
    property_record_id: str
    engineering_job_number: str
    link_status: str
    created_by: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PropertyEngineeringProposalRequestCreate(BaseModel):
    analysis_run_id: str | None = Field(default=None, max_length=36)
    project_goal: str = Field(min_length=2, max_length=2000)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: str = Field(min_length=3, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=80)

class PropertyEngineeringProposalRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    proposal_request_id: str
    property_record_id: str
    analysis_run_id: str | None
    project_goal: str
    customer_name: str
    customer_email: str
    customer_phone: str | None
    request_status: str
    source_product: str
    destination_product: str
    created_at: datetime


class PropertyEngineeringProposalPublicIntakeCreate(BaseModel):
    search_query: str = Field(min_length=3, max_length=500)
    analysis: dict[str, Any]
    project_goal: str = Field(min_length=2, max_length=2000)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: str = Field(min_length=3, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=80)


class PropertyEngineeringProposalPublicIntakeRead(BaseModel):
    property_record: PropertyRecordRead
    proposal_request: PropertyEngineeringProposalRequestRead


class PropertyPublicReportCreate(BaseModel):
    search_query: str = Field(min_length=2, max_length=500)
    analysis: dict[str, Any]
    project_goal: str | None = Field(default=None, max_length=2000)
    report_profile: str = Field(default="preliminary", min_length=3, max_length=20)


class PropertyEngineeringProposalRequestHistoryRead(PropertyEngineeringProposalRequestRead):
    proposal_lifecycle: dict[str, Any]


class PropertyEngineeringProposalStatusTransition(BaseModel):
    expected_current_status: str = Field(min_length=2, max_length=30)
    next_status: str = Field(min_length=2, max_length=30)


class PropertyEngineeringProposalDraftCreate(BaseModel):
    proposal_number: str = Field(min_length=1, max_length=100)
    proposal_date: str = Field(min_length=8, max_length=40)
    project_name: str | None = Field(default=None, max_length=300)
    services: list[dict[str, Any]] = Field(min_length=1)
    exclusions: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)


class EngineeringPropertyProposalDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    engineering_draft_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    proposal_status: str
    draft_snapshot: dict[str, Any]
    generated_by: str
    created_at: datetime


class EngineeringPropertyProposalReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    engineering_review_id: str
    engineering_draft_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    review_status: str
    approved_snapshot: dict[str, Any]
    reviewed_by: str
    created_at: datetime


class PropertyEngineeringProposalApprovalRead(BaseModel):
    review: EngineeringPropertyProposalReviewRead
    proposal_request_status: str
    proposal_lifecycle: dict[str, Any]
    engineering_job_created: bool


class EngineeringPropertyProposalReleaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    engineering_release_id: str
    engineering_review_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    release_status: str
    released_snapshot: dict[str, Any]
    released_by: str
    created_at: datetime


class PropertyEngineeringProposalReleaseActionRead(BaseModel):
    release: EngineeringPropertyProposalReleaseRead
    proposal_request_status: str
    proposal_lifecycle: dict[str, Any]
    engineering_job_created: bool
    client_approved: bool


class EngineeringPropertyProposalPdfArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    artifact_id: str
    engineering_release_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    filename: str
    mime_type: str
    pdf_sha256: str
    byte_size: int
    artifact_snapshot: dict[str, Any]
    created_by: str
    created_at: datetime


class PropertyEngineeringProposalPdfArtifactActionRead(BaseModel):
    artifact: EngineeringPropertyProposalPdfArtifactRead
    immutable: bool
    exact_bytes_persisted: bool
    automatic_send: bool


class PropertyEngineeringProposalClientResponseCreate(BaseModel):
    response_status: str = Field(pattern="^(ACCEPTED|DECLINED)$")


class EngineeringPropertyProposalClientResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    engineering_client_response_id: str
    engineering_release_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    response_status: str
    response_snapshot: dict[str, Any]
    recorded_by: str
    created_at: datetime


class PropertyEngineeringProposalClientResponseActionRead(BaseModel):
    client_response: EngineeringPropertyProposalClientResponseRead
    proposal_request_status: str
    proposal_lifecycle: dict[str, Any]
    engineering_job_created: bool
    engineering_job_creation_eligible: bool


class PropertyEngineeringProposalRequestContextRead(BaseModel):
    status: str
    proposal_request: PropertyEngineeringProposalRequestRead
    property_record: PropertyRecordRead
    analysis_run: PropertyAnalysisRunRead | None
    verification_summary: dict[str, Any]
    dynamic_intelligence_summary: dict[str, Any]
    proposal_lifecycle: dict[str, Any]
    professional_boundary: dict[str, Any]
    engineering_job_created: bool
    engineering_job_number: str | None = None


class PropertyEngineeringProposalDeliveryCreate(BaseModel):
    explicit_send_authorized: bool


class EngineeringPropertyProposalDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    engineering_delivery_id: str
    engineering_release_id: str
    artifact_id: str
    property_record_id: str
    proposal_request_id: str
    proposal_id: str
    proposal_number: str
    recipient: str
    delivery_status: str
    provider_message_id: str
    pdf_sha256: str
    delivery_snapshot: dict[str, Any]
    authorized_by: str
    created_at: datetime


class PropertyEngineeringProposalDeliveryActionRead(BaseModel):
    delivery: EngineeringPropertyProposalDeliveryRead
    exact_pdf_bytes_sent: bool
    automatic_send: bool
    client_response_recorded: bool
    engineering_job_created: bool
