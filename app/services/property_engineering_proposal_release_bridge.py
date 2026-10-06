"""Controlled Engineering client-release bridge for one approved Property-origin proposal."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.engineering_proposal_workflow import mark_proposal_sent


def release_property_engineering_proposal_to_client(
    *,
    approved_snapshot: dict[str, Any],
    engineering_user: str,
) -> dict[str, Any]:
    actor=str(engineering_user or "").strip()
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")
    if approved_snapshot.get("status") != "APPROVED_READY_TO_SEND":
        raise ValueError("only engineer-approved proposals may be released to the client")

    released=mark_proposal_sent(
        proposal=deepcopy(approved_snapshot),
        actor_role="MIDRA_ENGINEERING_STAFF",
    )
    released["released_by"]=actor
    released["release_channel"]="CLIENT_DELIVERY_ACTION"
    released["client_response_status"]="AWAITING_CLIENT_RESPONSE"
    released["engineering_job_created"]=False
    released["property_analysis_engineer_accepted"]=False
    released["professional_boundary"]={
        "proposal_engineer_approved":True,
        "proposal_released_to_client":True,
        "client_approved":False,
        "engineering_job_created":False,
        "property_analysis_engineer_accepted":False,
        "notice":(
            "MIDRA Engineering recorded a separate authorized client-release action for this approved proposal. "
            "Release does not mean the client accepted the proposal, does not create an Engineering job, and "
            "does not mark the underlying Property analysis Engineer Accepted."
        ),
    }
    return released
