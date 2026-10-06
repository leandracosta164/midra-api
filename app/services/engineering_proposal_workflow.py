"""Phase 5.29 controlled MIDRA Engineering proposal workflow.

Proposal drafting belongs exclusively to MIDRA Engineering.  Suggested scope
and prices come from an Engineering-owned service/pricing library and property
analysis signals, but the resulting proposal remains a private draft until an
authorized engineer reviews and approves it.  Nothing in this module sends a
proposal to a customer.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.services.engineering_intake_workspace import can_access_engineering_intake
from app.services.engineering_proposal_handoff import build_proposal_draft


def _text(value: Any) -> str:
    return str(value or "").strip()


def _money(value: Any) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _proposal_id(request_id: str, proposal_number: str) -> str:
    seed = f"{_text(request_id)}|{_text(proposal_number)}"
    return "MEP-" + sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def build_private_pricing_library(*, services: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize an Engineering-only service/pricing library."""
    normalized: dict[str, dict[str, Any]] = {}
    for item in services or []:
        key = _text(item.get("key")).lower()
        name = _text(item.get("service"))
        if not key or not name:
            continue
        normalized[key] = {
            "key": key,
            "service": name,
            "standard_price": str(_money(item.get("standard_price"))),
            "active": bool(item.get("active", True)),
        }
    return {
        "product_owner": "MIDRA_ENGINEERING",
        "visibility": "ENGINEERING_INTERNAL",
        "services": normalized,
    }


def suggest_scope_from_analysis(
    *, project_goal: str, analysis_signals: dict[str, Any], pricing_library: dict[str, Any]
) -> list[dict[str, Any]]:
    """Suggest scope deterministically from Engineering-controlled rules.

    This is not autonomous pricing.  The library owns the standard prices and
    the engineer can add/remove/edit every service before approval.
    """
    goal = _text(project_goal).lower()
    signals = analysis_signals or {}
    keys: list[str] = []

    # Base scope by project type.
    if any(token in goal for token in ("single-family", "single family", "new house", "dwelling")):
        keys.extend(["site_plot_plan", "grading_drainage"])
    elif "pool" in goal:
        keys.extend(["site_plot_plan", "grading_drainage"])
    elif any(token in goal for token in ("addition", "deck", "patio")):
        keys.append("site_plot_plan")

    # Analysis-driven conditional scope.
    if signals.get("stormwater_required") is True:
        keys.append("stormwater_management")
    if signals.get("sesc_required") is True:
        keys.append("sesc_plan")
    if signals.get("zoning_application_support") is True:
        keys.append("zoning_application_support")
    if signals.get("variance_support") is True:
        keys.append("variance_plan_support")

    services = pricing_library.get("services") or {}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        entry = services.get(key)
        if not entry or entry.get("active") is not True:
            continue
        result.append({"service_key": key, "service": entry["service"], "price": entry["standard_price"]})
    return result


def generate_proposal_for_review(
    *, intake: dict[str, Any], actor_role: str, proposal_number: str, proposal_date: str,
    project: str, property_address: str, prepared_for: str,
    suggested_services: list[dict[str, Any]], exclusions: list[str] | None = None,
    terms: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a private proposal draft; never approve or send automatically."""
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized to generate Engineering proposals")
    if intake.get("status") != "NEW_PROPOSAL_REQUEST":
        raise ValueError("proposal requires a NEW_PROPOSAL_REQUEST intake")

    draft = build_proposal_draft(
        proposal_number=proposal_number,
        proposal_date=proposal_date,
        project=project,
        property_address=property_address,
        prepared_for=prepared_for,
        services=[{"service": x.get("service"), "price": x.get("price")} for x in suggested_services],
        exclusions=exclusions,
        terms=terms,
    )
    draft["proposal_id"] = _proposal_id(_text(intake.get("request_id")), proposal_number)
    draft["request_id"] = intake.get("request_id")
    draft["scope_source"] = "ENGINEERING_CONTROLLED_LIBRARY_AND_ANALYSIS_SIGNALS"
    draft["manual_edit_allowed"] = True
    draft["send_allowed"] = False
    return draft


def revise_proposal_draft(
    *, proposal: dict[str, Any], actor_role: str, services: list[dict[str, Any]] | None = None,
    exclusions: list[str] | None = None, terms: list[str] | None = None,
) -> dict[str, Any]:
    """Allow Engineering to revise scope/prices while preserving draft status."""
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized to revise Engineering proposals")
    if proposal.get("status") != "DRAFT_REQUIRES_ENGINEER_REVIEW":
        raise ValueError("only review-required drafts can be revised")

    updated = deepcopy(proposal)
    if services is not None:
        normalized = []
        total = Decimal("0")
        for item in services:
            name = _text(item.get("service"))
            if not name:
                continue
            price = _money(item.get("price"))
            normalized.append({"service": name, "price": str(price)})
            total += price
        updated["scope_of_services"] = normalized
        updated["total_price"] = str(total.quantize(Decimal("0.01")))
    if exclusions is not None:
        updated["exclusions_additional_services"] = list(exclusions)
    if terms is not None:
        updated["terms"] = list(terms)
    updated["send_allowed"] = False
    updated["auto_send"] = False
    return updated


def approve_proposal(*, proposal: dict[str, Any], actor_role: str, approved_by: str) -> dict[str, Any]:
    """Record engineer approval. Approval makes the proposal send-eligible, not sent."""
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized to approve Engineering proposals")
    if proposal.get("status") != "DRAFT_REQUIRES_ENGINEER_REVIEW":
        raise ValueError("only review-required drafts can be approved")
    if not _text(approved_by):
        raise ValueError("approved_by is required")

    approved = deepcopy(proposal)
    approved["status"] = "APPROVED_READY_TO_SEND"
    approved["approved_by"] = _text(approved_by)
    approved["engineer_approval_required_before_send"] = False
    approved["send_allowed"] = True
    approved["auto_send"] = False
    approved["sent"] = False
    return approved


def mark_proposal_sent(*, proposal: dict[str, Any], actor_role: str) -> dict[str, Any]:
    """Record a separate authorized send action after approval.

    Transport/email delivery is intentionally outside this phase.
    """
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized to send Engineering proposals")
    if proposal.get("status") != "APPROVED_READY_TO_SEND" or proposal.get("send_allowed") is not True:
        raise ValueError("proposal must be engineer-approved before it can be marked sent")
    sent = deepcopy(proposal)
    sent["status"] = "SENT"
    sent["sent"] = True
    sent["send_allowed"] = False
    return sent


def revise_proposal_with_overrides(
    *, proposal: dict[str, Any], actor_role: str, services: list[dict[str, Any]],
    exclusions: list[str] | None = None, terms: list[str] | None = None,
) -> dict[str, Any]:
    """Revise a draft while retaining private standard-price provenance.

    The client-facing scope remains service + final price.  Internal metadata
    records the library price and whether the engineer overrode it.
    """
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("actor is not authorized to revise Engineering proposals")
    if proposal.get("status") != "DRAFT_REQUIRES_ENGINEER_REVIEW":
        raise ValueError("only review-required drafts can be revised")

    updated = deepcopy(proposal)
    normalized = []
    total = Decimal("0")
    for item in services or []:
        name = _text(item.get("service"))
        if not name:
            continue
        final_price = _money(item.get("price"))
        standard_raw = item.get("standard_price", item.get("price"))
        standard_price = _money(standard_raw)
        row = {
            "service": name,
            "price": str(final_price),
            "service_key": _text(item.get("service_key")).lower() or None,
            "pricing_version_id": item.get("pricing_version_id"),
            "price_source": item.get("price_source") or "ENGINEER_MANUAL_ENTRY",
            "standard_price_internal": str(standard_price),
            "engineer_price_override": final_price != standard_price,
        }
        normalized.append(row)
        total += final_price
    updated["scope_of_services"] = normalized
    updated["total_price"] = str(total.quantize(Decimal("0.01")))
    if exclusions is not None:
        updated["exclusions_additional_services"] = list(exclusions)
    if terms is not None:
        updated["terms"] = list(terms)
    updated["send_allowed"] = False
    updated["auto_send"] = False
    return updated
