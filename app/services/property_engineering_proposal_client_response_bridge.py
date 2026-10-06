"""Controlled client-response bridge for released Property-origin Engineering proposals."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


CLIENT_RESPONSE_STATUSES = {"ACCEPTED", "DECLINED"}


def record_property_engineering_proposal_client_response(
    *,
    released_snapshot: dict[str, Any],
    response_status: str,
    engineering_user: str,
) -> dict[str, Any]:
    actor=str(engineering_user or "").strip()
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")

    response=str(response_status or "").strip().upper()
    if response not in CLIENT_RESPONSE_STATUSES:
        raise ValueError("client response must be ACCEPTED or DECLINED")

    if released_snapshot.get("status") != "SENT" or released_snapshot.get("sent") is not True:
        raise ValueError("proposal must be released to the client before a response may be recorded")
    if str(released_snapshot.get("client_response_status") or "").strip().upper() != "AWAITING_CLIENT_RESPONSE":
        raise ValueError("released proposal is not awaiting a client response")

    result=deepcopy(released_snapshot)
    result["client_response_status"]=response
    result["client_response_recorded_by"]=actor
    result["client_response_recorded_at"]=datetime.now(timezone.utc).isoformat()
    result["client_approved"]=response=="ACCEPTED"
    result["engineering_job_created"]=False
    result["property_analysis_engineer_accepted"]=False
    result["professional_boundary"]={
        "proposal_engineer_approved":True,
        "proposal_released_to_client":True,
        "client_approved":response=="ACCEPTED",
        "engineering_job_created":False,
        "property_analysis_engineer_accepted":False,
        "notice":(
            "MIDRA Engineering recorded the client's explicit proposal response. "
            "Acceptance makes the proposal eligible for a separate authorized Engineering "
            "job-creation action; it does not itself create a job or mark Property analysis "
            "Engineer Accepted."
        ),
    }
    return result
