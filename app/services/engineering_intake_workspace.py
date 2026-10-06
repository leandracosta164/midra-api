"""Phase 5.28 secure cross-product engineering intake/workspace contracts.

MIDRA Intelligence and MIDRA Engineering remain separate products while using
shared MIDRA platform records.  A proposal request creates an Engineering
intake that references the existing property analysis/evidence snapshot.  It
does not grant Engineering-wide access to ordinary Intelligence users and does
not require duplicate property research.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any

_ENGINEERING_ROLES = {"MIDRA_ENGINEERING_STAFF", "MIDRA_ADMIN"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _request_id(*, analysis_id: str, property_record_id: str, project_goal: str) -> str:
    seed = "|".join([analysis_id.strip(), property_record_id.strip(), project_goal.strip().lower()])
    return "MER-" + sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def create_engineering_intake(
    *,
    handoff: dict[str, Any],
    property_record_id: str,
    analysis_snapshot_id: str | None = None,
) -> dict[str, Any]:
    """Create the Engineering-side intake reference after an explicit request."""
    if handoff.get("status") != "ENGINEERING_PROPOSAL_REQUESTED":
        raise ValueError("handoff must be an ENGINEERING_PROPOSAL_REQUESTED record")
    if handoff.get("source_product") != "MIDRA_INTELLIGENCE":
        raise ValueError("handoff must originate from MIDRA_INTELLIGENCE")
    if handoff.get("destination_product") != "MIDRA_ENGINEERING":
        raise ValueError("handoff must target MIDRA_ENGINEERING")

    analysis_id = _text(handoff.get("analysis_id"))
    property_record_id = _text(property_record_id)
    if not analysis_id or not property_record_id:
        raise ValueError("analysis_id and property_record_id are required")

    project_goal = _text(handoff.get("project_goal"))
    return {
        "status": "NEW_PROPOSAL_REQUEST",
        "request_id": _request_id(
            analysis_id=analysis_id,
            property_record_id=property_record_id,
            project_goal=project_goal,
        ),
        "source_product": "MIDRA_INTELLIGENCE",
        "destination_product": "MIDRA_ENGINEERING",
        "shared_platform_reference": {
            "property_record_id": property_record_id,
            "analysis_id": analysis_id,
            "analysis_snapshot_id": _text(analysis_snapshot_id) or None,
        },
        "project_goal": project_goal,
        "customer": deepcopy(handoff.get("customer") or {}),
        "customer_report_profile": _text(handoff.get("customer_report_profile") or "PRELIMINARY").upper(),
        "customer_entitlement_unchanged": True,
        "duplicate_property_research_required": False,
        "proposal": {
            "status": "NOT_GENERATED",
            "auto_send": False,
            "engineer_review_required": True,
        },
    }


def can_access_engineering_intake(*, actor_role: str) -> bool:
    """Engineering intake is private to Engineering staff/admin roles."""
    return _text(actor_role).upper() in _ENGINEERING_ROLES


def build_engineering_workspace(
    *,
    intake: dict[str, Any],
    actor_role: str,
    shared_property_record: dict[str, Any],
    shared_analysis: dict[str, Any],
    shared_evidence_package: dict[str, Any],
) -> dict[str, Any]:
    """Resolve an Engineering workspace from referenced shared-platform data.

    Callers must load the shared records identified by the intake reference.
    This function validates those identities before exposing the workspace.
    """
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized for MIDRA Engineering intake")
    if intake.get("destination_product") != "MIDRA_ENGINEERING":
        raise ValueError("intake does not target MIDRA_ENGINEERING")

    ref = intake.get("shared_platform_reference") or {}
    expected_property_id = _text(ref.get("property_record_id"))
    expected_analysis_id = _text(ref.get("analysis_id"))
    actual_property_id = _text(shared_property_record.get("property_record_id") or shared_property_record.get("id"))
    actual_analysis_id = _text(shared_analysis.get("analysis_id") or shared_analysis.get("id"))
    if not expected_property_id or actual_property_id != expected_property_id:
        raise ValueError("shared property record does not match intake reference")
    if not expected_analysis_id or actual_analysis_id != expected_analysis_id:
        raise ValueError("shared analysis does not match intake reference")

    artifacts = deepcopy(shared_evidence_package.get("artifacts") or [])
    return {
        "status": "ENGINEERING_WORKSPACE_READY",
        "product": "MIDRA_ENGINEERING",
        "request_id": intake.get("request_id"),
        "shared_platform_reference": deepcopy(ref),
        "project_goal": intake.get("project_goal"),
        "customer": deepcopy(intake.get("customer") or {}),
        "property_record": deepcopy(shared_property_record),
        "analysis": deepcopy(shared_analysis),
        "evidence_package": deepcopy(shared_evidence_package),
        "tabs": {
            "overview": True,
            "property": True,
            "zoning": True,
            "project_analysis": True,
            "maps": True,
            "documents": True,
            "sources": True,
            "proposal": True,
        },
        "map_access": {
            "midra_integrated_map": True,
            "zoning_map": any(a.get("artifact_type") == "ZONING_MAP" for a in artifacts),
            "tax_map": any(a.get("artifact_type") == "TAX_MAP" for a in artifacts),
            "original_downloads": True,
        },
        "customer_entitlement_unchanged": True,
        "duplicate_property_research_required": False,
        "proposal": deepcopy(intake.get("proposal") or {}),
    }
