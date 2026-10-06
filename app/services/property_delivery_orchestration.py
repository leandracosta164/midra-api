"""Phase 5.27 orchestration for MIDRA Intelligence property delivery.

This layer composes Phase 5.26 contracts without collapsing product boundaries:
- one master property/evidence record;
- customer report entitlement is a presentation/export choice, not a data-loss choice;
- the property workspace keeps original map artifacts viewable/downloadable;
- an Engineering handoff is created only after the user requests a proposal;
- the handoff references the same analysis/evidence snapshot rather than re-researching.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.engineering_proposal_handoff import build_engineering_handoff
from app.services.property_evidence_artifacts import build_property_evidence_package
from app.services.property_report_manifest import build_report_manifest


def _text(value: Any) -> str:
    return str(value or "").strip()


def _workspace_artifact(item: dict[str, Any]) -> dict[str, Any]:
    """Expose preserved artifact metadata to the Intelligence workspace."""
    return {
        "artifact_id": item.get("artifact_id"),
        "artifact_type": item.get("artifact_type"),
        "label": item.get("label"),
        "source_url": item.get("source_url"),
        "tax_map_sheet": item.get("tax_map_sheet"),
        "official_source_verified": bool(item.get("official_source_verified")),
        "view_original": bool((item.get("workspace") or {}).get("view_original")),
        "download_original": bool((item.get("workspace") or {}).get("download_original")),
    }


def build_property_delivery_bundle(
    *,
    analysis_id: str,
    property_record: dict[str, Any],
    project_goal: str,
    sources: list[dict[str, Any]],
    environmental_screening: dict[str, Any] | None = None,
    zoning_candidate_evidence: dict[str, Any] | None = None,
    dynamic_intelligence_evidence: dict[str, Any] | None = None,
    verification_summary: dict[str, Any] | None = None,
    report_profile: str = "preliminary",
    analysis_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one Intelligence delivery bundle from one master evidence package.

    The bundle intentionally retains all discovered evidence even when the customer
    selects the Preliminary report.  Report composition never deletes or downgrades
    the master evidence record.
    """
    municipality = _text(property_record.get("municipality"))
    if not municipality:
        raise ValueError("property_record.municipality is required")

    evidence = build_property_evidence_package(
        municipality=municipality,
        block=_text(property_record.get("block")) or None,
        lot=_text(property_record.get("lot")) or None,
        sources=list(sources or []),
    )
    screening = deepcopy(environmental_screening or {})
    if screening:
        evidence["screening_evidence"] = screening
    zoning_candidate = deepcopy(zoning_candidate_evidence or {})
    if zoning_candidate:
        evidence["zoning_candidate_evidence"] = zoning_candidate
    dynamic_intelligence = deepcopy(dynamic_intelligence_evidence or {})
    if dynamic_intelligence:
        evidence["dynamic_intelligence_evidence"] = dynamic_intelligence
    verification = deepcopy(verification_summary or {})
    if verification:
        evidence["verification_summary"] = verification
    report = build_report_manifest(report_profile=report_profile, evidence_package=evidence)
    snapshot = deepcopy(analysis_snapshot or {})

    return {
        "status": "PROPERTY_DELIVERY_READY",
        "product": "MIDRA_INTELLIGENCE",
        "analysis_id": analysis_id,
        "project_goal": project_goal,
        "property_record": deepcopy(property_record),
        "analysis_snapshot": snapshot,
        "master_evidence_package": evidence,
        "workspace": {
            "midra_integrated_map": True,
            "map_artifacts": [_workspace_artifact(item) for item in evidence.get("artifacts", [])],
            "environmental_screening": deepcopy(screening),
            "zoning_candidate_evidence": deepcopy(zoning_candidate),
            "dynamic_intelligence_evidence": deepcopy(dynamic_intelligence),
            "verification_summary": deepcopy(verification),
        },
        "customer_report": report,
        "customer_report_profile": report["report_profile"],
        "complete_evidence_retained_independent_of_report": True,
        "engineering_proposal_request": {
            "available": True,
            "created": False,
            "destination_product": "MIDRA_ENGINEERING",
            "cta_copy": {
                "headline": "Ready to move forward with your project?",
                "body": "Engineering design services are available through MIDRA Engineering.",
                "action": "REQUEST AN ENGINEERING PROPOSAL",
            },
        },
    }


def request_engineering_proposal(
    *, delivery_bundle: dict[str, Any], customer: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create the explicit Intelligence -> Engineering intake from a delivery bundle."""
    if delivery_bundle.get("product") != "MIDRA_INTELLIGENCE":
        raise ValueError("delivery_bundle must originate from MIDRA_INTELLIGENCE")
    if not delivery_bundle.get("analysis_id"):
        raise ValueError("delivery_bundle.analysis_id is required")

    return build_engineering_handoff(
        analysis_id=str(delivery_bundle["analysis_id"]),
        customer_report_profile=str(delivery_bundle.get("customer_report_profile") or "PRELIMINARY"),
        property_record=deepcopy(delivery_bundle.get("property_record") or {}),
        project_goal=str(delivery_bundle.get("project_goal") or ""),
        evidence_package=deepcopy(delivery_bundle.get("master_evidence_package") or {"artifacts": []}),
        customer=deepcopy(customer or {}),
        analysis_snapshot=deepcopy(delivery_bundle.get("analysis_snapshot") or {}),
    )
