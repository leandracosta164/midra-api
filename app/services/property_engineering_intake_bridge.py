"""Property proposal -> protected MIDRA Engineering intake projection.

The durable Property proposal request remains the source record. This bridge
resolves the exact referenced Property analysis into the existing Engineering
intake/workspace contracts without creating an Engineering job.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.engineering_proposal_handoff import build_engineering_handoff
from app.services.engineering_intake_workspace import (
    build_engineering_workspace,
    create_engineering_intake,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def build_property_engineering_intake_bridge(
    *,
    proposal_request: dict[str, Any],
    property_record: dict[str, Any],
    analysis_id: str,
    analysis_snapshot: dict[str, Any],
    evidence_package: dict[str, Any],
    engineering_user: str,
) -> dict[str, Any]:
    """Project one exact durable Property proposal into Engineering intake."""
    property_record_id=_text(property_record.get("property_record_id"))
    proposal_request_id=_text(proposal_request.get("proposal_request_id"))
    exact_analysis_id=_text(analysis_id)
    actor=_text(engineering_user)

    if not property_record_id or not proposal_request_id or not exact_analysis_id:
        raise ValueError("property, proposal request, and exact analysis identity are required")
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")
    if _text(proposal_request.get("property_record_id")) != property_record_id:
        raise ValueError("proposal request does not belong to the Property record")
    request_analysis_id=_text(proposal_request.get("analysis_run_id"))
    if not request_analysis_id or request_analysis_id != exact_analysis_id:
        raise ValueError("proposal request does not reference the exact Property analysis")

    customer={
        "name":_text(proposal_request.get("customer_name")),
        "email":_text(proposal_request.get("customer_email")),
        "phone":_text(proposal_request.get("customer_phone")) or None,
    }
    project_goal=_text(proposal_request.get("project_goal"))
    handoff=build_engineering_handoff(
        analysis_id=exact_analysis_id,
        customer_report_profile="COMPLETE",
        property_record=deepcopy(property_record),
        project_goal=project_goal,
        evidence_package=deepcopy(evidence_package),
        customer=customer,
        analysis_snapshot=deepcopy(analysis_snapshot),
    )
    intake=create_engineering_intake(
        handoff=handoff,
        property_record_id=property_record_id,
        analysis_snapshot_id=exact_analysis_id,
    )
    workspace=build_engineering_workspace(
        intake=intake,
        actor_role="MIDRA_ENGINEERING_STAFF",
        shared_property_record=deepcopy(property_record),
        shared_analysis={
            "analysis_id":exact_analysis_id,
            "analysis_snapshot_id":exact_analysis_id,
            "analysis":deepcopy(analysis_snapshot),
        },
        shared_evidence_package=deepcopy(evidence_package),
    )
    return {
        "status":"ENGINEERING_PROPERTY_PROPOSAL_INTAKE_READY",
        "source_product":"MIDRA_PROPERTY",
        "destination_product":"MIDRA_ENGINEERING",
        "property_proposal_request_id":proposal_request_id,
        "engineering_user":actor,
        "intake":intake,
        "workspace":workspace,
        "proposal":{
            "status":"NOT_GENERATED",
            "engineer_review_required":True,
            "auto_send":False,
        },
        "professional_boundary":{
            "engineer_reviewed":False,
            "engineer_accepted":False,
            "engineering_job_created":False,
            "notice":(
                "The Engineering intake references the exact MIDRA Property analysis. "
                "It does not create a job, approve a proposal, or mark Property "
                "Intelligence engineer-reviewed or accepted."
            ),
        },
    }
