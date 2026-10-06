"""Delivery adapter for durable MIDRA Property verification context."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_delivery_verification_summary(analysis: dict[str, Any] | None) -> dict[str, Any]:
    """Carry saved verification state into delivery without reinterpreting it."""
    analysis = analysis or {}
    all_items = deepcopy(list(analysis.get("verification_items") or []))
    zoning_items = deepcopy(list(analysis.get("zoning_candidate_verification_items") or []))
    environmental_items = deepcopy(list(analysis.get("environmental_verification_items") or []))
    if not all_items and not zoning_items and not environmental_items:
        return {}
    requires_verification = bool(all_items or zoning_items or environmental_items)
    return {
        "status": "VERIFICATION_REQUIRED" if requires_verification else "VERIFICATION_CONTEXT_AVAILABLE",
        "items": all_items,
        "zoning_candidate_items": zoning_items,
        "environmental_items": environmental_items,
        "professional_boundary": {
            "engineer_reviewed": False,
            "engineer_accepted": False,
            "notice": (
                "Verification items remain MIDRA Analysis context and do not "
                "constitute engineer review or acceptance."
            ),
        },
    }
