"""MIDRA Intelligence -> MIDRA Engineering handoff contracts.

The public products remain separate. The proposal request transfers/references
an existing MIDRA analysis into the Engineering intake so the property is not
researched from zero. There is intentionally no separate permission-screen
state in this service contract; disclosure/privacy copy can be handled by the
request UI/policies later.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def build_engineering_handoff(
    *, analysis_id: str, customer_report_profile: str, property_record: dict[str, Any],
    project_goal: str, evidence_package: dict[str, Any], customer: dict[str, Any] | None = None,
    analysis_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "ENGINEERING_PROPOSAL_REQUESTED",
        "source_product": "MIDRA_INTELLIGENCE",
        "destination_product": "MIDRA_ENGINEERING",
        "handoff_mode": "SHARED_PLATFORM_REFERENCE",
        "duplicate_property_research_required": False,
        "analysis_id": analysis_id,
        "analysis_snapshot": analysis_snapshot or {},
        "preserve_customer_analysis_snapshot": True,
        "allow_current_analysis_refresh": True,
        "project_goal": project_goal,
        "property_record": property_record,
        "customer": customer or {},
        "customer_report_profile": str(customer_report_profile or "PRELIMINARY").upper(),
        # Engineering access is independent from the customer's purchased/exported
        # report profile. This does not expand the customer's report entitlement.
        "engineering_access": {
            "complete_property_record": True,
            "complete_analysis": True,
            "all_evidence_artifacts": True,
            "maps": True,
            "zoning_map": True,
            "tax_map": True,
            "source_documents": True,
            "original_map_downloads": True,
        },
        "customer_entitlement_unchanged": True,
        "evidence_package": evidence_package,
        "separate_share_permission_step": False,
        "cta_copy": {
            "headline": "Ready to move forward with your project?",
            "body": "Engineering design services are available through MIDRA Engineering.",
            "action": "REQUEST AN ENGINEERING PROPOSAL",
        },
    }


def build_proposal_draft(
    *, proposal_number: str, proposal_date: str, project: str, property_address: str,
    prepared_for: str, services: list[dict[str, Any]], exclusions: list[str] | None = None,
    terms: list[str] | None = None,
) -> dict[str, Any]:
    """Build a private MIDRA Engineering review-required proposal/estimate draft."""
    normalized = []
    total = Decimal("0")
    for item in services or []:
        name = str(item.get("service") or "").strip()
        if not name:
            continue
        price = Decimal(str(item.get("price") or "0"))
        normalized.append({"service": name, "price": str(price.quantize(Decimal("0.01")))})
        total += price

    return {
        "product_owner": "MIDRA_ENGINEERING",
        "visibility": "ENGINEERING_INTERNAL_UNTIL_APPROVED",
        "status": "DRAFT_REQUIRES_ENGINEER_REVIEW",
        "auto_send": False,
        "engineer_approval_required_before_send": True,
        "branding": "MIDRA_ENGINEERING",
        "layout": {
            "logo_position": "TOP_LEFT",
            "proposal_number_position": "TOP_RIGHT",
            "date_position": "TOP_RIGHT",
            "proposal_title_position": "CENTER_BELOW_HEADER",
        },
        "proposal_number": proposal_number,
        "date": proposal_date,
        "title": "PROPOSAL",
        "project": project,
        "property_address": property_address,
        "prepared_for": prepared_for,
        "scope_of_services": normalized,
        "scope_descriptions": False,
        "professional_fees_section": False,
        "total_price": str(total.quantize(Decimal("0.01"))),
        "exclusions_additional_services": list(exclusions or []),
        "terms": list(terms or []),
        "accept_proposal_section": True,
    }
