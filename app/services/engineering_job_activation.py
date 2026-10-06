"""Phase 5.57 — accepted proposal -> authorized Job activation and automatic setup."""
from datetime import datetime, timezone

def job_activation_review(*, proposal, client, property_record):
    """Prepare everything for review; acceptance alone never creates a Job."""
    if not proposal.get("accepted_by_client"):
        raise ValueError("proposal must be accepted by client")
    return {
        "proposal_id": proposal["proposal_id"],
        "request_id": proposal.get("request_id"),
        "client_id": client["client_id"],
        "property_address": property_record["property_address"],
        "scope": list(proposal.get("scope", [])),
        "approved_fee": proposal.get("selected_fee"),
        "source": proposal.get("source", "ENGINEERING_REQUEST"),
        "status": "REQUIRES_JOB_ACTIVATION_REVIEW",
        "job_number": None,
        "job_created": False,
    }

def next_job_number(*, year, existing_job_numbers):
    """Sequential number from the authoritative Job Database."""
    prefix=f"{year}-"
    nums=[]
    for value in existing_job_numbers:
        if str(value).startswith(prefix):
            tail=str(value)[len(prefix):]
            if tail.isdigit(): nums.append(int(tail))
    return f"{year}-{(max(nums,default=0)+1):03d}"

def authorize_job_activation(*, review, job_number, authorized_by, activated_at=None):
    if not authorized_by.strip(): raise ValueError("job activation requires authorized human")
    if review.get("status")!="REQUIRES_JOB_ACTIVATION_REVIEW":
        raise ValueError("invalid activation state")
    r=dict(review)
    r.update({"status":"ACTIVE","job_number":job_number,"job_created":True,
              "authorized_by":authorized_by,
              "activated_at":activated_at or datetime.now(timezone.utc).isoformat()})
    return r

def build_initial_job_setup(*, activation):
    if not activation.get("job_created"): raise ValueError("job must be activated first")
    n=activation["job_number"]
    return {
        "job":{
            "job_number":n,"client_id":activation["client_id"],
            "property_address":activation["property_address"],
            "source":activation["source"],"job_status":"ACTIVE",
            "current_stage":"PROJECT_SETUP","scope":list(activation["scope"]),
        },
        "repository":{
            "repository_id":f"REPO:{n}","job_number":n,
            "storage_scope":"MIDRA_MANAGED_PROJECT_STORAGE",
        },
        "financial":{
            "job_number":n,"accepted_proposal_id":activation["proposal_id"],
            "approved_fee":activation.get("approved_fee"),
        },
        "workflow":{
            "job_number":n,"next_action":"REVIEW_INITIAL_PROJECT_SETUP",
            "requires_human_review":True,
        },
    }

def carry_forward_project_context(*, setup, property_analysis=None, proposal_artifacts=None):
    """Reuse existing information instead of asking the engineer to enter it again."""
    return {
        **setup,
        "carried_forward":{
            "property_analysis":property_analysis,
            "proposal_artifacts":list(proposal_artifacts or []),
            "manual_reentry_required":False,
        },
    }

def activation_policy():
    return {
        "client_acceptance_creates_job_automatically":False,
        "authorized_activation_required":True,
        "job_number_source":"AUTHORITATIVE_JOB_DATABASE",
        "duplicate_data_entry_required":False,
    }
