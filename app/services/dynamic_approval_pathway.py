"""Safe evaluation of dynamically discovered approval-pathway evidence.

This module is intentionally isolated from the established approval-pathway
builder. Dynamic sources may propose a pathway, but the proposal is only
promotable when the evidence explicitly establishes legal control.
"""
from __future__ import annotations

from typing import Any


def evaluate_dynamic_approval_pathway(candidate: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate a dynamic approval-pathway candidate without mutating legacy state."""
    if not candidate:
        return _verify("No dynamic approval-pathway evidence was supplied.")

    requirements = list(candidate.get("requirements") or [])
    if not requirements:
        return _verify("No approval-pathway requirements were supplied by the dynamic evidence.")

    authoritative = candidate.get("authoritative") is True
    legal_control_confirmed = candidate.get("legal_control_confirmed") is True
    if not authoritative or not legal_control_confirmed:
        return _verify(
            "Dynamic approval-pathway evidence is not legally confirmed and must be verified."
        )

    primary = candidate.get("primary_pathway")
    if not primary:
        return _verify("The dynamic evidence does not explicitly identify a primary approval pathway.")

    reviewing_bodies = [str(x) for x in (candidate.get("reviewing_bodies") or []) if str(x).strip()]
    possible_alternative = candidate.get("possible_alternative")

    return {
        "status": "AVAILABLE",
        "promotable": True,
        "primary_pathway": str(primary),
        "possible_alternative": str(possible_alternative) if possible_alternative else None,
        "reviewing_bodies": reviewing_bodies,
        "requirements": requirements,
        "source": candidate.get("source"),
        "authoritative": True,
        "legal_control_confirmed": True,
        "reason": "Approval-pathway evidence is explicitly identified and legally confirmed.",
    }


def _verify(reason: str) -> dict[str, Any]:
    return {
        "status": "VERIFY",
        "promotable": False,
        "primary_pathway": None,
        "possible_alternative": None,
        "reviewing_bodies": [],
        "requirements": [],
        "source": None,
        "authoritative": False,
        "legal_control_confirmed": False,
        "reason": reason,
    }
