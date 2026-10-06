"""Protected Property proposal -> MIDRA Engineering proposal-draft bridge.

This bridge consumes the exact Engineering intake created from a durable Property
proposal request and generates a private review-required Engineering proposal draft.
Pricing is never invented here: every service/price pair must be supplied explicitly
by an authenticated Engineering user. Generating a draft does not send a proposal,
approve it, or create an Engineering job.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.engineering_proposal_workflow import generate_proposal_for_review
from app.services.property_engineering_proposal_context import build_dynamic_engineering_handoff_summary
from app.services.property_verification_delivery import build_delivery_verification_summary


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_services(services: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in services or []:
        name = _text(item.get("service"))
        if not name:
            continue
        raw_price = item.get("price")
        if raw_price in (None, ""):
            raise ValueError(f"Engineering price is required for service: {name}")
        try:
            price = Decimal(str(raw_price)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"invalid Engineering price for service: {name}") from exc
        if price < 0:
            raise ValueError(f"Engineering price cannot be negative for service: {name}")
        normalized.append({"service": name, "price": str(price)})
    if not normalized:
        raise ValueError("at least one Engineering-selected service with an explicit price is required")
    return normalized


def build_property_engineering_proposal_draft(
    *,
    intake_bridge: dict[str, Any],
    engineering_user: str,
    proposal_number: str,
    proposal_date: str,
    services: list[dict[str, Any]],
    project_name: str | None = None,
    exclusions: list[str] | None = None,
    terms: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a private Engineering proposal draft from the exact Property intake."""
    if intake_bridge.get("status") != "ENGINEERING_PROPERTY_PROPOSAL_INTAKE_READY":
        raise ValueError("proposal draft requires an exact Engineering Property intake")
    actor = _text(engineering_user)
    if not actor:
        raise PermissionError("authenticated Engineering user identity is required")

    intake = dict(intake_bridge.get("intake") or {})
    workspace = dict(intake_bridge.get("workspace") or {})
    property_record = dict(workspace.get("property_record") or {})
    customer = dict(workspace.get("customer") or intake.get("customer") or {})
    shared_ref = dict(workspace.get("shared_platform_reference") or intake.get("shared_platform_reference") or {})

    if intake.get("status") != "NEW_PROPOSAL_REQUEST":
        raise ValueError("Engineering proposal draft requires a NEW_PROPOSAL_REQUEST intake")
    if not _text(shared_ref.get("property_record_id")) or not _text(shared_ref.get("analysis_id")):
        raise ValueError("exact Property record and analysis lineage are required")

    normalized_services = _normalize_services(services)
    project_goal = _text(workspace.get("project_goal") or intake.get("project_goal"))
    address = _text(property_record.get("address") or property_record.get("display_address"))
    prepared_for = _text(customer.get("name"))
    if not _text(proposal_number) or not _text(proposal_date):
        raise ValueError("proposal number and proposal date are required")
    if not address or not prepared_for:
        raise ValueError("Property address and customer name are required for proposal drafting")

    proposal = generate_proposal_for_review(
        intake=intake,
        actor_role="MIDRA_ENGINEERING_STAFF",
        proposal_number=_text(proposal_number),
        proposal_date=_text(proposal_date),
        project=_text(project_name) or project_goal or "Engineering Services",
        property_address=address,
        prepared_for=prepared_for,
        suggested_services=normalized_services,
        exclusions=list(exclusions or []),
        terms=list(terms or []),
    )
    workspace_analysis = dict(workspace.get("analysis") or {})
    analysis_snapshot = dict(workspace_analysis.get("analysis") or {})
    verification_summary = build_delivery_verification_summary(analysis_snapshot)
    dynamic_intelligence_summary = build_dynamic_engineering_handoff_summary(analysis_snapshot)

    proposal.update({
        "source_product": "MIDRA_PROPERTY",
        "destination_product": "MIDRA_ENGINEERING",
        "property_proposal_request_id": intake_bridge.get("property_proposal_request_id"),
        "property_record_id": shared_ref.get("property_record_id"),
        "analysis_id": shared_ref.get("analysis_id"),
        "analysis_snapshot_id": shared_ref.get("analysis_snapshot_id"),
        "engineering_user": actor,
        "pricing_source": "ENGINEERING_EXPLICIT_INPUT",
        "property_research_reused": True,
        "duplicate_property_research_required": False,
        "engineering_job_created": False,
        "property_intelligence_context": {
            "analysis_id": shared_ref.get("analysis_id"),
            "analysis_snapshot_id": shared_ref.get("analysis_snapshot_id"),
            "verification_summary": verification_summary,
            "dynamic_intelligence_summary": dynamic_intelligence_summary,
            "professional_boundary": {
                "engineer_reviewed": False,
                "engineer_accepted": False,
                "notice": (
                    "Property intelligence context is preserved for Engineering review only. "
                    "Generating or approving the proposal does not itself constitute Engineer "
                    "Reviewed or Engineer Accepted Property analysis."
                ),
            },
        },
    })
    proposal["professional_boundary"] = {
        "engineer_reviewed": False,
        "engineer_accepted": False,
        "proposal_sent": False,
        "engineering_job_created": False,
        "notice": (
            "This is a private MIDRA Engineering proposal draft generated from the exact "
            "Property proposal intake. It requires authorized Engineering review before "
            "approval or release and does not create an Engineering job."
        ),
    }
    return proposal
