"""Report composition contract for MIDRA Preliminary and Complete reports."""
from __future__ import annotations

from typing import Any


def build_report_manifest(
    *,
    report_profile: str,
    evidence_package: dict[str, Any] | None,
) -> dict[str, Any]:
    profile = str(report_profile or "").strip().lower()
    if profile not in {"preliminary", "complete"}:
        raise ValueError("report_profile must be 'preliminary' or 'complete'")

    artifacts = list((evidence_package or {}).get("artifacts") or [])
    screening_evidence = dict((evidence_package or {}).get("screening_evidence") or {})
    zoning_candidate_evidence = dict((evidence_package or {}).get("zoning_candidate_evidence") or {})
    dynamic_intelligence_evidence = dict((evidence_package or {}).get("dynamic_intelligence_evidence") or {})
    verification_summary = dict((evidence_package or {}).get("verification_summary") or {})
    verification_context = {}
    if verification_summary:
        verification_items = list(verification_summary.get("items") or [])
        environmental_items = list(verification_summary.get("environmental_items") or [])
        zoning_candidate_items = list(verification_summary.get("zoning_candidate_items") or [])
        verification_context = {
            "status": verification_summary.get("status"),
            "item_count": len(verification_items),
            "environmental_item_count": len(environmental_items),
            "zoning_candidate_item_count": len(zoning_candidate_items),
            "requires_verification": bool(
                verification_items or environmental_items or zoning_candidate_items
            ),
            "professional_boundary": dict(
                verification_summary.get("professional_boundary") or {}
            ),
        }
    included_artifacts = []
    if profile == "complete":
        included_artifacts = [
            item for item in artifacts
            if (item.get("report_eligibility") or {}).get("complete") is True
            and item.get("artifact_type") in {"ZONING_MAP", "TAX_MAP"}
        ]

    return {
        "report_profile": profile.upper(),
        "branding": "MIDRA_INTELLIGENCE",
        "sections": {
            "midra_property_map": True,
            "zoning_map_exhibit": profile == "complete",
            "tax_map_exhibit": profile == "complete",
            "expanded_evidence": profile == "complete",
            "source_index": profile == "complete",
            "environmental_screening": bool(screening_evidence),
            "environmental_source_index": profile == "complete" and bool(screening_evidence),
            "zoning_candidate_geometry": bool(zoning_candidate_evidence),
            "zoning_candidate_source_index": profile == "complete" and bool(zoning_candidate_evidence),
            "dynamic_intelligence": bool(dynamic_intelligence_evidence),
            "dynamic_source_index": profile == "complete" and bool(dynamic_intelligence_evidence),
            "verification_summary": bool(verification_summary),
        },
        "verification_context": verification_context,
        "artifact_ids": [item.get("artifact_id") for item in included_artifacts],
        "customer_entitlement_scope": profile.upper(),
    }
