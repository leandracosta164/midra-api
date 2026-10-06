"""Authorized Engineering review bridge for one exact durable Property-origin proposal draft."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.engineering_proposal_workflow import approve_proposal


def approve_property_engineering_proposal_draft(
    *,
    draft_snapshot: dict[str, Any],
    engineering_user: str,
) -> dict[str, Any]:
    actor=str(engineering_user or "").strip()
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")
    if draft_snapshot.get("status") != "DRAFT_REQUIRES_ENGINEER_REVIEW":
        raise ValueError("only review-required Engineering proposal drafts may be approved")

    approved=approve_proposal(
        proposal=deepcopy(draft_snapshot),
        actor_role="MIDRA_ENGINEERING_STAFF",
        approved_by=actor,
    )
    approved["source_product"] = draft_snapshot.get("source_product") or "MIDRA_PROPERTY"
    approved["destination_product"] = "MIDRA_ENGINEERING"
    approved["property_record_id"] = draft_snapshot.get("property_record_id")
    approved["property_proposal_request_id"] = draft_snapshot.get("property_proposal_request_id")
    approved["analysis_id"] = draft_snapshot.get("analysis_id")
    approved["analysis_snapshot_id"] = draft_snapshot.get("analysis_snapshot_id")
    approved["engineering_job_created"] = False
    approved["proposal_sent"] = False
    approved["professional_boundary"] = {
        "proposal_engineer_approved": True,
        "property_analysis_engineer_accepted": False,
        "proposal_sent": False,
        "engineering_job_created": False,
        "notice": (
            "An authorized MIDRA Engineering user approved this proposal for a separate client release step. "
            "This approval does not send the proposal, create an Engineering job, or by itself mark the "
            "underlying Property analysis Engineer Accepted."
        ),
    }
    return approved
