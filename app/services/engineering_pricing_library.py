"""Phase 5.29A Engineering-owned service catalog, pricing versions and scope templates.

Pricing is private MIDRA Engineering business data.  MIDRA Intelligence may
supply applicability signals, but it never owns, invents, or mutates prices.
Proposal snapshots copy the selected service name/price/version so later
library changes cannot rewrite an existing proposal.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.services.engineering_intake_workspace import can_access_engineering_intake


def _text(value: Any) -> str:
    return str(value or "").strip()


def _money(value: Any) -> str:
    return str(Decimal(str(value or "0")).quantize(Decimal("0.01")))


def _require_engineering(actor_role: str) -> None:
    if not can_access_engineering_intake(actor_role=actor_role):
        raise PermissionError("Engineering pricing is private to MIDRA Engineering")


def _stable_id(prefix: str, *parts: str) -> str:
    seed = "|".join(_text(p) for p in parts)
    return prefix + sha256(seed.encode("utf-8")).hexdigest()[:12].upper()


def build_service_catalog(*, services: list[dict[str, Any]], actor_role: str) -> dict[str, Any]:
    """Create the Engineering-owned catalog without exposing prices publicly."""
    _require_engineering(actor_role)
    normalized: dict[str, dict[str, Any]] = {}
    for item in services or []:
        key = _text(item.get("key")).lower()
        name = _text(item.get("service"))
        if not key or not name:
            continue
        normalized[key] = {
            "key": key,
            "service": name,
            "category": _text(item.get("category")) or "ENGINEERING_SERVICE",
            "active": bool(item.get("active", True)),
        }
    return {
        "product_owner": "MIDRA_ENGINEERING",
        "visibility": "ENGINEERING_INTERNAL",
        "services": normalized,
    }


def create_pricing_version(
    *, catalog: dict[str, Any], prices: dict[str, Any], version_label: str,
    effective_date: str, actor_role: str,
) -> dict[str, Any]:
    """Create an immutable pricing version for active catalog services."""
    _require_engineering(actor_role)
    label = _text(version_label)
    effective = _text(effective_date)
    if not label or not effective:
        raise ValueError("version_label and effective_date are required")
    # Validate ISO date without imposing today's date on tests/callers.
    date.fromisoformat(effective)
    service_prices: dict[str, str] = {}
    for key, value in (prices or {}).items():
        k = _text(key).lower()
        service = (catalog.get("services") or {}).get(k)
        if not service or service.get("active") is not True:
            continue
        service_prices[k] = _money(value)
    return {
        "pricing_version_id": _stable_id("MPV-", label, effective),
        "version_label": label,
        "effective_date": effective,
        "product_owner": "MIDRA_ENGINEERING",
        "visibility": "ENGINEERING_INTERNAL",
        "immutable": True,
        "prices": service_prices,
    }


def build_project_scope_template(
    *, project_type: str, default_services: list[str] | None = None,
    conditional_services: list[dict[str, Any]] | None = None, actor_role: str,
) -> dict[str, Any]:
    """Define owner-controlled default and conditional scope for a project type."""
    _require_engineering(actor_role)
    project = _text(project_type).lower()
    if not project:
        raise ValueError("project_type is required")
    defaults = [_text(k).lower() for k in (default_services or []) if _text(k)]
    conditionals = []
    for item in conditional_services or []:
        key = _text(item.get("service_key")).lower()
        signal = _text(item.get("signal"))
        if key and signal:
            conditionals.append({"service_key": key, "signal": signal, "expected": item.get("expected", True)})
    return {
        "template_id": _stable_id("MST-", project),
        "product_owner": "MIDRA_ENGINEERING",
        "visibility": "ENGINEERING_INTERNAL",
        "project_type": project,
        "default_services": defaults,
        "conditional_services": conditionals,
    }


def resolve_template_scope(
    *, template: dict[str, Any], analysis_signals: dict[str, Any], catalog: dict[str, Any],
    pricing_version: dict[str, Any], actor_role: str,
) -> list[dict[str, Any]]:
    """Resolve suggested scope using template rules + MIDRA applicability signals."""
    _require_engineering(actor_role)
    keys = list(template.get("default_services") or [])
    signals = analysis_signals or {}
    for rule in template.get("conditional_services") or []:
        if signals.get(rule.get("signal")) == rule.get("expected", True):
            keys.append(rule.get("service_key"))

    result = []
    seen: set[str] = set()
    services = catalog.get("services") or {}
    prices = pricing_version.get("prices") or {}
    for raw_key in keys:
        key = _text(raw_key).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        service = services.get(key)
        if not service or service.get("active") is not True or key not in prices:
            continue
        result.append({
            "service_key": key,
            "service": service["service"],
            "price": prices[key],
            "pricing_version_id": pricing_version.get("pricing_version_id"),
            "price_source": "ENGINEERING_PRICING_LIBRARY",
        })
    return result


def freeze_proposal_snapshot(*, proposal: dict[str, Any], actor_role: str) -> dict[str, Any]:
    """Freeze scope/prices after approval; future library changes cannot mutate it."""
    _require_engineering(actor_role)
    if proposal.get("status") != "APPROVED_READY_TO_SEND":
        raise ValueError("only an approved proposal can be frozen")
    snapshot = deepcopy(proposal)
    snapshot["scope_price_snapshot_frozen"] = True
    snapshot["pricing_snapshot"] = deepcopy(proposal.get("scope_of_services") or [])
    snapshot["pricing_snapshot_total"] = _text(proposal.get("total_price"))
    snapshot["library_updates_apply_retroactively"] = False
    snapshot["manual_edit_allowed"] = False
    return snapshot
