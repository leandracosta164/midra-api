"""Resolve an existing Property -> Engineering proposal request into shared-platform context."""
from __future__ import annotations

from typing import Any

from app.services.property_verification_delivery import build_delivery_verification_summary
from app.services.property_engineering_proposal_lifecycle import classify_property_engineering_proposal_lifecycle


def build_dynamic_engineering_handoff_summary(
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    dynamic = (analysis or {}).get("dynamic_intelligence") or {}
    if not isinstance(dynamic, dict) or not dynamic:
        return {"status":"NO_DYNAMIC_INTELLIGENCE","available":False,"verification_required":False}

    project_intent=dict(dynamic.get("project_intent") or {})
    zoning=dict(dynamic.get("zoning") or {})
    candidate=dict(zoning.get("candidate") or {})
    record=dict(candidate.get("record") or {})
    promotion=dict(zoning.get("promotion") or {})
    applicability=dict(dynamic.get("project_applicability") or {})
    approval=dict(dynamic.get("approval_pathway") or {})
    approval_candidate=dict(dynamic.get("approval_pathway_candidate") or {})
    source_trust=dict(dynamic.get("source_trust_summary") or {})

    primary_pathway=approval.get("primary_pathway") or approval_candidate.get("primary_pathway")
    reviewing_bodies=list(approval.get("reviewing_bodies") or []) or list(approval_candidate.get("reviewing_bodies") or [])
    verification_required=any((
        dynamic.get("dynamic_promotable") is not True,
        promotion.get("promotable") is not True,
        applicability.get("status")=="VERIFY",
        applicability.get("promotable") is False,
        approval.get("status")=="VERIFY",
        approval.get("promotable") is False,
    ))

    return {
        "status":"DYNAMIC_INTELLIGENCE_CONTEXT_AVAILABLE",
        "available":True,
        "dynamic_promotable":dynamic.get("dynamic_promotable") is True,
        "verification_required":verification_required,
        "project_intent":project_intent,
        "zoning":{
            "district":record.get("zoning_district"),
            "promotion_status":promotion.get("status"),
            "promotion_reason":promotion.get("reason"),
            "promotable":promotion.get("promotable") is True,
        },
        "project_applicability":{
            "status":applicability.get("status"),
            "reason":applicability.get("reason"),
            "promotable":applicability.get("promotable") is True,
        },
        "approval_pathway":{
            "status":approval.get("status"),
            "primary_pathway":primary_pathway,
            "reviewing_bodies":reviewing_bodies,
            "reason":approval.get("reason"),
            "promotable":approval.get("promotable") is True,
        },
        "source_trust":{
            "trust_state":source_trust.get("trust_state"),
            "verification_required":source_trust.get("verification_required") is True,
            "authority_confirmed":((source_trust.get("official_representation") or {}).get("confirmed") is True),
            "legal_control_confirmed":((source_trust.get("legal_control") or {}).get("confirmed") is True),
            "current_status":((source_trust.get("source_currentness") or {}).get("current_status")),
            "last_checked_at":((source_trust.get("source_currentness") or {}).get("last_checked_at")),
        },
        "professional_boundary":{
            "engineer_reviewed":False,
            "engineer_accepted":False,
            "notice":"Dynamic statewide evidence remains MIDRA Analysis context and is not engineer review or acceptance.",
        },
    }


# Historical default when no authorized job creation exists: "engineering_job_created": False
def build_property_engineering_proposal_context(
    *,
    proposal_request: Any,
    property_record: Any,
    analysis_run: Any | None,
    engineering_job_creation: Any | None = None,
) -> dict[str, Any]:
    analysis = getattr(analysis_run, "analysis", None) if analysis_run is not None else None
    verification_summary = build_delivery_verification_summary(analysis or {})
    dynamic_intelligence_summary = build_dynamic_engineering_handoff_summary(analysis or {})
    proposal_lifecycle = classify_property_engineering_proposal_lifecycle(
        getattr(proposal_request, "request_status", None)
    )
    engineering_job_created = engineering_job_creation is not None
    engineering_job_number = getattr(engineering_job_creation, "engineering_job_number", None) if engineering_job_created else None
    if engineering_job_created:
        proposal_lifecycle = {
            **proposal_lifecycle,
            "state": "ENGINEERING_JOB_CREATED",
            "job_creation_eligible": False,
            "job_creation_completed": True,
            "next_required_event": None,
        }
    has_analysis = analysis_run is not None
    return {
        "status": (
            "PROPERTY_ENGINEERING_PROPOSAL_CONTEXT_READY"
            if has_analysis
            else "PROPERTY_ENGINEERING_PROPOSAL_CONTEXT_PROPERTY_ONLY"
        ),
        "proposal_request": proposal_request,
        "property_record": property_record,
        "analysis_run": analysis_run,
        "verification_summary": verification_summary,
        "dynamic_intelligence_summary": dynamic_intelligence_summary,
        "proposal_lifecycle": proposal_lifecycle,
        "professional_boundary": {
            "engineer_reviewed": False,
            "engineer_accepted": False,
            "notice": (
                "Resolved Property context remains MIDRA Analysis until an authorized "
                "engineer reviews and explicitly accepts it into the Engineering record."
            ),
        },
        "engineering_job_created": engineering_job_created,
        "engineering_job_number": engineering_job_number,
    }
