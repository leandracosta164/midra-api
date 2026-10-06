"""Authorized conversion of an accepted Property-origin proposal into an Engineering job."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.engineering_unified_intake import assign_job_number


def _text(value: Any) -> str:
    return str(value or "").strip()


def build_authorized_engineering_job_creation(
    *,
    property_record: Any,
    proposal_request: Any,
    client_response: Any,
    engineering_user: str,
    existing_job_numbers: list[str],
    year: int | None = None,
) -> dict[str, Any]:
    actor=_text(engineering_user)
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")
    if _text(getattr(proposal_request,"request_status",None)).upper() != "CLIENT_APPROVED":
        raise ValueError("Engineering job creation requires a CLIENT_APPROVED proposal request")
    if _text(getattr(client_response,"response_status",None)).upper() != "ACCEPTED":
        raise ValueError("Engineering job creation requires an ACCEPTED client response")

    response_snapshot=dict(getattr(client_response,"response_snapshot",None) or {})
    if _text(response_snapshot.get("client_response_status")).upper() != "ACCEPTED":
        raise ValueError("accepted client response snapshot is required")
    if response_snapshot.get("client_approved") is not True:
        raise ValueError("client approval must be explicit before Engineering job creation")
    if response_snapshot.get("engineering_job_created") is not False:
        raise ValueError("client response snapshot already indicates an Engineering job")

    proposal_id=_text(getattr(client_response,"proposal_id",None))
    proposal_number=_text(getattr(client_response,"proposal_number",None))
    if not proposal_id or not proposal_number:
        raise ValueError("accepted proposal identity is required")

    now=datetime.now(timezone.utc)
    job_number=assign_job_number(year=year or now.year, existing_job_numbers=existing_job_numbers)
    property_address=_text(getattr(property_record,"display_address",None) or getattr(property_record,"search_query",None))
    project_goal=_text(getattr(proposal_request,"project_goal",None))
    project_name=_text(response_snapshot.get("project") or response_snapshot.get("project_name") or project_goal or property_address or "Engineering Services")
    project_type=(project_goal or "Engineering Services")[:100]
    analysis_run_id=_text(getattr(proposal_request,"analysis_run_id",None)) or None

    sections={
        "client":{
            "reference_id":getattr(proposal_request,"proposal_request_id",None),
            "summary":{
                "name":getattr(proposal_request,"customer_name",None),
                "email":getattr(proposal_request,"customer_email",None),
                "phone":getattr(proposal_request,"customer_phone",None),
                "description":"Client identity from accepted MIDRA Property proposal request.",
            },
            "updated_by":actor,
        },
        "property":{
            "reference_id":getattr(property_record,"property_record_id",None),
            "summary":{
                "analysis_run_id":analysis_run_id,
                "address":property_address,
                "municipality":getattr(property_record,"municipality",None),
                "county":getattr(property_record,"county",None),
                "block":getattr(property_record,"block",None),
                "lot":getattr(property_record,"lot",None),
                "property_analysis_engineer_accepted":False,
                "description":"Exact MIDRA Property lineage retained for Engineering review; Property analysis is not automatically Engineer Accepted.",
            },
            "updated_by":actor,
        },
        "estimate":{
            "reference_id":proposal_id,
            "summary":{
                "proposal_number":proposal_number,
                "proposal_request_id":getattr(proposal_request,"proposal_request_id",None),
                "client_response_id":getattr(client_response,"engineering_client_response_id",None),
                "client_response":"ACCEPTED",
                "description":"Accepted Engineering proposal that authorized job setup.",
            },
            "updated_by":actor,
        },
        "workflow":{
            "reference_id":f"SETUP-{job_number}",
            "summary":{"stage":"PROJECT_SETUP","description":"Engineering job created after explicit client acceptance."},
            "updated_by":actor,
        },
    }
    event={
        "event_type":"JOB_CREATED_FROM_ACCEPTED_PROPERTY_PROPOSAL",
        "reference_id":getattr(proposal_request,"proposal_request_id",None),
        "proposal_id":proposal_id,
        "proposal_number":proposal_number,
        "client_response_id":getattr(client_response,"engineering_client_response_id",None),
        "property_record_id":getattr(property_record,"property_record_id",None),
        "analysis_run_id":analysis_run_id,
        "authorized_by":actor,
        "occurred_at":now.isoformat(),
    }
    snapshot={
        "status":"ENGINEERING_JOB_CREATED",
        "engineering_job_number":job_number,
        "property_record_id":getattr(property_record,"property_record_id",None),
        "analysis_run_id":analysis_run_id,
        "proposal_request_id":getattr(proposal_request,"proposal_request_id",None),
        "proposal_id":proposal_id,
        "proposal_number":proposal_number,
        "engineering_job_created":True,
        "property_analysis_engineer_accepted":False,
        "created_by":actor,
        "created_at":now.isoformat(),
        "professional_boundary":{
            "proposal_client_approved":True,
            "engineering_job_created":True,
            "property_analysis_engineer_accepted":False,
            "notice":"Creating the Engineering job opens the authorized Engineering workspace. It does not automatically mark MIDRA Property analysis Engineer Accepted.",
        },
    }
    return {
        "job":{
            "job_number":job_number,
            "project_name":project_name[:300],
            "project_type":project_type,
            "source":"MIDRA_PROPERTY",
            "property_address":property_address or None,
            "client_id":None,
            "state":"ACTIVE",
            "version":1,
            "sections":sections,
            "events":[event],
            "created_at":now,
            "updated_at":now,
        },
        "creation_snapshot":snapshot,
    }
