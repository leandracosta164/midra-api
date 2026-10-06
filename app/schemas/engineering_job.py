"""Pydantic schemas for MIDRA Engineering Job operations."""
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EngineeringJobCreate(BaseModel):
    job_number: str = Field(min_length=1, max_length=50)
    project_name: str = Field(min_length=1, max_length=300)
    project_type: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    property_address: str | None = Field(default=None, max_length=500)
    client_id: str | None = Field(default=None, max_length=100)


class EngineeringJobStateChange(BaseModel):
    state: str = Field(min_length=1, max_length=50)
    authorized_by: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=1000)


class EngineeringJobSectionConnect(BaseModel):
    section: str = Field(min_length=1, max_length=100)
    reference_id: str = Field(min_length=1, max_length=200)
    summary: dict[str, Any] = Field(default_factory=dict)
    authorized_by: str | None = Field(default=None, max_length=200)


class EngineeringJobEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=100)
    reference_id: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=2000)


class EngineeringJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_number: str
    project_name: str
    project_type: str
    source: str
    property_address: str | None
    client_id: str | None
    state: str
    version: int
    sections: dict[str, Any]
    events: list[Any]


class EngineeringJobProfileUpdate(BaseModel):
    project_name: str = Field(min_length=1, max_length=300)
    project_type: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    property_address: str | None = Field(default=None, max_length=500)
    client_id: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=1000)


class EngineeringJobSignalCreate(BaseModel):
    signal_type: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=1000)
    level: str = Field(default="NORMAL", min_length=1, max_length=20)
    waiting_on: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=50)
    requires_user_action: bool = False
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringJobSignalResolve(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)
    resolution: str | None = Field(default=None, max_length=1000)


class EngineeringDeliverableCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    deliverable_type: str = Field(min_length=1, max_length=80)
    recipient: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDeliverableStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    reference: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    professional_action_approved: bool = False
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDocumentUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=200)
    content_base64: str = Field(min_length=1)
    category: str = Field(default="OTHER", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    deliverable_id: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDocumentRevisionUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=200)
    content_base64: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=2000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringReviewCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    reviewer: str | None = Field(default=None, max_length=300)
    review_date: str | None = Field(default=None, max_length=50)
    source_document_id: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringReviewCommentCreate(BaseModel):
    comment_number: str = Field(min_length=1, max_length=50)
    comment_text: str = Field(min_length=1, max_length=5000)
    discipline: str | None = Field(default=None, max_length=100)
    due_at: str | None = Field(default=None, max_length=50)
    requires_action: bool = True
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringReviewCommentUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    response_text: str | None = Field(default=None, max_length=5000)
    resolution_note: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionPackageCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    recipient: str = Field(min_length=1, max_length=300)
    submission_type: str = Field(default="AGENCY", min_length=1, max_length=50)
    due_at: str | None = Field(default=None, max_length=50)
    method: str | None = Field(default=None, max_length=100)
    deliverable_ids: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionPackageStatusChange(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    submitted_at: str | None = Field(default=None, max_length=50)
    reference: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=3000)
    professional_approval: bool = False
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDependencyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    waiting_on: str = Field(min_length=1, max_length=300)
    dependency_type: str = Field(default="EXTERNAL", min_length=1, max_length=50)
    due_at: str | None = Field(default=None, max_length=50)
    follow_up_at: str | None = Field(default=None, max_length=50)
    related_review_id: str | None = Field(default=None, max_length=100)
    related_package_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDependencyUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    due_at: str | None = Field(default=None, max_length=50)
    follow_up_at: str | None = Field(default=None, max_length=50)
    resolution_note: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringActionItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    action_type: str = Field(default="ENGINEERING", min_length=1, max_length=50)
    owner: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=50)
    priority: str = Field(default="NORMAL", min_length=1, max_length=30)
    related_review_id: str | None = Field(default=None, max_length=100)
    related_package_id: str | None = Field(default=None, max_length=100)
    related_dependency_id: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringActionItemUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    owner: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=50)
    priority: str | None = Field(default=None, max_length=30)
    completion_note: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringLifecycleAuditAcknowledgementRead(BaseModel):
    acknowledgement_id: str
    acknowledgement_notes: str
    acknowledged_by: str
    acknowledged_at: str
    audit_snapshot: dict = Field(default_factory=dict)


class EngineeringLifecycleAuditAcknowledgementCreate(BaseModel):
    acknowledgement_notes: str = Field(min_length=1, max_length=10000)
    acknowledged_by: str = Field(min_length=1, max_length=200)


class EngineeringPostCompletionWorkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    work_type: str = Field(default="OTHER", min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringPostCompletionWorkUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    resolution_notes: str | None = Field(default=None, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringProjectReopenCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringProjectCompletionCertificationCreate(BaseModel):
    certification_type: str = Field(default="PROJECT_COMPLETE", min_length=1, max_length=50)
    completion_date: str = Field(min_length=1, max_length=100)
    certification_notes: str = Field(min_length=1, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringProjectClosureItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    closure_type: str = Field(default="OTHER", min_length=1, max_length=50)
    responsible_party: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringProjectClosureItemUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    completion_notes: str | None = Field(default=None, max_length=10000)
    responsible_party: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringArchiveRecordCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    record_type: str = Field(default="OTHER", min_length=1, max_length=50)
    retention_until: str | None = Field(default=None, max_length=100)
    storage_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringArchiveRecordUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    verification_notes: str | None = Field(default=None, max_length=10000)
    retention_until: str | None = Field(default=None, max_length=100)
    storage_reference: str | None = Field(default=None, max_length=1000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringWarrantyIssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    location: str | None = Field(default=None, max_length=500)
    responsible_party: str | None = Field(default=None, max_length=300)
    priority: str = Field(default="NORMAL", min_length=1, max_length=50)
    warranty_expires_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringWarrantyIssueUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    resolution_notes: str | None = Field(default=None, max_length=10000)
    responsible_party: str | None = Field(default=None, max_length=300)
    priority: str | None = Field(default=None, max_length=50)
    warranty_expires_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringCloseoutItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    item_type: str = Field(default="OTHER", min_length=1, max_length=50)
    responsible_party: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringCloseoutItemUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    completion_notes: str | None = Field(default=None, max_length=10000)
    responsible_party: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringPunchItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    location: str | None = Field(default=None, max_length=500)
    responsible_party: str | None = Field(default=None, max_length=300)
    priority: str = Field(default="NORMAL", min_length=1, max_length=50)
    due_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringPunchItemUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    resolution_notes: str | None = Field(default=None, max_length=10000)
    responsible_party: str | None = Field(default=None, max_length=300)
    priority: str | None = Field(default=None, max_length=50)
    due_at: str | None = Field(default=None, max_length=100)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringChangeOrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    requested_by: str | None = Field(default=None, max_length=300)
    cost_impact: str | None = Field(default=None, max_length=300)
    schedule_impact: str | None = Field(default=None, max_length=300)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringChangeOrderUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    decision_notes: str | None = Field(default=None, max_length=10000)
    decided_by: str | None = Field(default=None, max_length=300)
    cost_impact: str | None = Field(default=None, max_length=300)
    schedule_impact: str | None = Field(default=None, max_length=300)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmittalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    submittal_type: str = Field(default="SHOP_DRAWING", min_length=1, max_length=50)
    submitted_by: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=10000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringSubmittalReview(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    review_notes: str | None = Field(default=None, max_length=10000)
    reviewed_by: str | None = Field(default=None, max_length=300)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringRFICreate(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    question: str = Field(min_length=1, max_length=10000)
    requested_from: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    priority: str = Field(default="NORMAL", min_length=1, max_length=30)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringRFIUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    response: str | None = Field(default=None, max_length=10000)
    responded_by: str | None = Field(default=None, max_length=300)
    due_at: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=30)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringFieldReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    report_type: str = Field(default="SITE_VISIT", min_length=1, max_length=50)
    observed_at: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=300)
    observations: str = Field(min_length=1, max_length=10000)
    follow_up_required: bool = False
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringFieldReportUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    observations: str | None = Field(default=None, max_length=10000)
    follow_up_required: bool | None = None
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringMeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    meeting_type: str = Field(default="PROJECT", min_length=1, max_length=50)
    scheduled_at: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=300)
    attendees: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=5000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringMeetingUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    scheduled_at: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=300)
    attendees: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringMilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    milestone_type: str = Field(default="PROJECT", min_length=1, max_length=50)
    due_at: str | None = Field(default=None, max_length=100)
    owner: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringMilestoneUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    due_at: str | None = Field(default=None, max_length=100)
    owner: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringCorrespondenceCreate(BaseModel):
    direction: str = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=500)
    channel: str = Field(default="EMAIL", min_length=1, max_length=50)
    sender: str | None = Field(default=None, max_length=300)
    recipient: str | None = Field(default=None, max_length=300)
    occurred_at: str | None = Field(default=None, max_length=50)
    response_required: bool = False
    response_due_at: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringCorrespondenceResponseUpdate(BaseModel):
    response_status: str = Field(min_length=1, max_length=30)
    response_due_at: str | None = Field(default=None, max_length=50)
    response_note: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringBillingCreate(BaseModel):
    billing_type: str = Field(min_length=1, max_length=50)
    reference: str = Field(min_length=1, max_length=300)
    status: str = Field(default="DRAFT", min_length=1, max_length=30)
    issued_at: str | None = Field(default=None, max_length=50)
    due_at: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringBillingStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringClientPortalItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    item_type: str = Field(default="DOCUMENT", min_length=1, max_length=50)
    status: str = Field(default="DRAFT", min_length=1, max_length=30)
    acknowledgement_required: bool = False
    client_action_required: bool = False
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)

class EngineeringClientPortalItemUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    acknowledgement_status: str | None = Field(default=None, max_length=30)
    client_action_status: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringDocumentRevisionStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=3000)
    professional_approval: bool = False
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringReviewCycleStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=3000)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionReadinessAssess(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionPackageAdvance(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionOutcomeRecord(BaseModel):
    outcome: str = Field(min_length=1, max_length=30)
    authorized_by: str = Field(min_length=1, max_length=200)
    reference: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=3000)


class EngineeringSubmissionReturnWorkActivate(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)
    owner: str | None = Field(default=None, max_length=200)
    due_at: str | None = Field(default=None, max_length=100)
    priority: str = Field(default="HIGH", min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=3000)


class EngineeringReturnedSubmissionReassess(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)


class EngineeringSubmissionResubmissionOpen(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)
    resubmission_note: str | None = Field(default=None, max_length=3000)


class EngineeringAcceptedSubmissionClose(BaseModel):
    authorized_by: str = Field(min_length=1, max_length=200)
    closure_note: str | None = Field(default=None, max_length=3000)


class EngineeringSubmissionLifecycleAttention(BaseModel):
    package_id: str | None = None
    title: str | None = None
    status: str
    outcome: str | None = None
    open_return_work: int = 0

class EngineeringSubmissionLifecycleSummary(BaseModel):
    job_number: str
    package_count: int
    status_counts: dict[str, int]
    attention_packages: list[EngineeringSubmissionLifecycleAttention]

