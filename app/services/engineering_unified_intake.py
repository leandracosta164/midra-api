"""Phase 5.41 Revised — unified MIDRA Engineering intake, job numbering and lifecycle foundation."""
from __future__ import annotations
from datetime import datetime, timezone

REQUEST_SOURCES = {
    "MIDRA_PROPERTY",
    "MIDRA_ENGINEERING_WEBSITE",
    "PHONE",
    "EMAIL",
    "REFERRAL",
    "MANUAL",
    "OTHER",
}

PROJECT_STAGES = (
    "PROJECT_SETUP", "DESIGN", "READY_FOR_SUBMISSION", "UNDER_REVIEW",
    "REVISIONS", "APPROVED", "COMPLETED", "CLOSED",
)

_ALLOWED_TRANSITIONS = {
    "PROJECT_SETUP": {"DESIGN"},
    "DESIGN": {"READY_FOR_SUBMISSION"},
    "READY_FOR_SUBMISSION": {"UNDER_REVIEW", "DESIGN"},
    "UNDER_REVIEW": {"REVISIONS", "APPROVED"},
    "REVISIONS": {"READY_FOR_SUBMISSION"},
    "APPROVED": {"COMPLETED"},
    "COMPLETED": {"CLOSED"},
    "CLOSED": set(),
}


def create_engineering_request(*, client: dict, property_address: str, project_goal: str,
                               source: str, created_by: str) -> dict:
    if source not in REQUEST_SOURCES:
        raise ValueError("unsupported request source")
    if not property_address.strip() or not project_goal.strip() or not created_by.strip():
        raise ValueError("request requires address, project goal and creator")
    return {
        "client": dict(client),
        "property_address": property_address,
        "project_goal": project_goal,
        "source": source,
        "created_by": created_by,
        "property_analysis_status": "NOT_RUN",
        "property_record_id": None,
        "analysis_id": None,
        "analysis_snapshot_id": None,
    }


def attach_midra_property_analysis(*, request: dict, analysis: dict) -> dict:
    """Manual/automatic MIDRA Property analysis attachment uses the same shared engine lineage."""
    required = ("property_record_id", "analysis_id", "analysis_snapshot_id")
    if any(not analysis.get(k) for k in required):
        raise ValueError("MIDRA Property analysis lineage incomplete")
    result = dict(request)
    result.update({
        "property_analysis_status": "COMPLETE",
        "property_record_id": analysis["property_record_id"],
        "analysis_id": analysis["analysis_id"],
        "analysis_snapshot_id": analysis["analysis_snapshot_id"],
        "midra_property_analysis": dict(analysis),
    })
    return result


def midra_property_analysis_action(*, request: dict) -> dict:
    """Explicit manual action offered for phone/email/referral/manual Engineering requests."""
    return {
        "label": "MIDRA PROPERTY ANALYSIS",
        "action": "RUN_SHARED_MIDRA_PROPERTY_ENGINE",
        "property_address": request["property_address"],
        "project_goal": request["project_goal"],
    }


def assign_job_number(*, year: int, existing_job_numbers: list[str]) -> str:
    """Return next sequential Engineering job number for the given year."""
    prefix = f"{year}-"
    seqs = []
    for value in existing_job_numbers:
        if value.startswith(prefix):
            suffix = value[len(prefix):]
            if suffix.isdigit():
                seqs.append(int(suffix))
    return f"{year}-{(max(seqs, default=0) + 1):03d}"


def convert_accepted_request_to_job(*, request: dict, accepted_proposal: dict,
                                    authorized_by: str, existing_job_numbers: list[str],
                                    year: int, created_at: str | None = None) -> dict:
    if accepted_proposal.get("response") != "ACCEPTED":
        raise ValueError("job creation requires accepted proposal")
    if not authorized_by.strip():
        raise ValueError("job creation requires authorized Engineering action")
    job_number = assign_job_number(year=year, existing_job_numbers=existing_job_numbers)
    return {
        "job_number": job_number,
        "job_status": "ACTIVE",
        "current_stage": "PROJECT_SETUP",
        "source": request["source"],
        "client": dict(request["client"]),
        "property_address": request["property_address"],
        "project_goal": request["project_goal"],
        "property_record_id": request.get("property_record_id"),
        "analysis_id": request.get("analysis_id"),
        "analysis_snapshot_id": request.get("analysis_snapshot_id"),
        "proposal_id": accepted_proposal.get("proposal_id"),
        "created_by": authorized_by,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "history": [{"event": "JOB_CREATED", "stage": "PROJECT_SETUP"}],
        "milestones": [],
    }


def transition_job_stage(*, job: dict, to_stage: str, authorized_by: str) -> dict:
    current = job["current_stage"]
    if to_stage not in PROJECT_STAGES or to_stage not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError("invalid project lifecycle transition")
    if not authorized_by.strip():
        raise ValueError("transition requires authorized actor")
    result = dict(job)
    result["history"] = [dict(x) for x in job.get("history", [])]
    result["history"].append({"event": "STAGE_CHANGED", "from": current, "to": to_stage,
                              "authorized_by": authorized_by})
    result["current_stage"] = to_stage
    return result


def job_database_projection(*, jobs: list[dict]) -> list[dict]:
    """All Engineering jobs live together; origin is metadata/filtering, not separate storage."""
    return [{
        "job_number": j["job_number"],
        "client": j.get("client"),
        "property_address": j.get("property_address"),
        "project_goal": j.get("project_goal"),
        "source": j.get("source"),
        "status": j.get("job_status"),
        "stage": j.get("current_stage"),
    } for j in jobs]
