"""Phase 5.64 — project-aware communication drafting with human send control."""

SUPPORTED_TYPES={
    "CLIENT_EMAIL","AGENCY_FOLLOWUP","DOCUMENT_TRANSMITTAL",
    "INFORMATION_REQUEST","STATUS_UPDATE","RESPONSE_EMAIL"
}

def build_communication_context(*,job,correspondence=None,documents=None,project_status=None):
    return {
        "job_number":job["job_number"],
        "property_address":job.get("property_address"),
        "client_id":job.get("client_id"),
        "municipality":job.get("municipality"),
        "correspondence":dict(correspondence) if correspondence else None,
        "documents":[dict(x) for x in (documents or [])],
        "project_status":dict(project_status or {}),
    }

def create_communication_draft(*,communication_type,context,recipient=None,subject=None,
                               requested_message=None):
    if communication_type not in SUPPORTED_TYPES:
        raise ValueError("unsupported communication type")
    return {
        "communication_type":communication_type,
        "job_number":context["job_number"],
        "property_address":context.get("property_address"),
        "recipient":recipient,
        "subject":subject,
        "requested_message":requested_message,
        "context":context,
        "status":"DRAFT_REQUIRES_REVIEW",
        "send_authorized":False,
        "sent":False,
    }

def revise_communication_draft(*,draft,subject=None,message=None,recipient=None,authorized_by):
    if not authorized_by.strip():
        raise ValueError("authorized reviewer required")
    r=dict(draft)
    if subject is not None: r["subject"]=subject
    if message is not None: r["message"]=message
    if recipient is not None: r["recipient"]=recipient
    r["status"]="REVIEWED_DRAFT"
    r["reviewed_by"]=authorized_by
    return r

def authorize_communication_send(*,draft,authorized_by):
    if draft.get("status")!="REVIEWED_DRAFT":
        raise ValueError("communication must be reviewed before send authorization")
    if not authorized_by.strip():
        raise ValueError("send authorization required")
    if not draft.get("recipient"):
        raise ValueError("recipient required before send authorization")
    r=dict(draft)
    r["status"]="APPROVED_FOR_SEND"
    r["send_authorized"]=True
    r["send_authorized_by"]=authorized_by
    return r

def mark_communication_sent(*,draft,delivery_reference):
    if not draft.get("send_authorized"):
        raise ValueError("communication is not authorized for sending")
    if not delivery_reference:
        raise ValueError("delivery reference required")
    r=dict(draft)
    r["status"]="SENT"
    r["sent"]=True
    r["delivery_reference"]=delivery_reference
    return r

def communication_filing_record(*,sent_communication):
    if not sent_communication.get("sent"):
        raise ValueError("only sent communication may be filed as sent correspondence")
    return {
        "job_number":sent_communication["job_number"],
        "document_area":"CORRESPONDENCE",
        "direction":"OUTGOING",
        "communication_type":sent_communication["communication_type"],
        "delivery_reference":sent_communication["delivery_reference"],
    }

def drafting_policy():
    return {
        "reuse_known_project_context":True,
        "automatic_sending":False,
        "review_required_before_send":True,
        "recipient_must_be_known_or_selected":True,
        "manual_retyping_project_information_required":False,
        "sent_correspondence_returns_to_project_record":True,
    }
