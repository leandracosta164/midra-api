"""Safe bridge for dynamically discovered project-rule evidence.

This layer accepts project-specific rule evidence discovered from municipal
sources, but never treats a discovered source as legally controlling merely
because it contains plausible-looking rules. The established rule registry
remains untouched.
"""
from __future__ import annotations

from typing import Any

from app.services.rule_applicability import evaluate_project_rule_applicability


def build_dynamic_project_rule_candidate(
    *,
    municipality: str,
    zoning_district: str,
    project_goal: str,
    requirements: list[dict[str, Any]] | None,
    source: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a non-authoritative dynamic project-rule candidate."""
    if not str(municipality or "").strip():
        return {"status": "VERIFY", "reason": "MUNICIPALITY_MISSING"}
    if not str(zoning_district or "").strip():
        return {"status": "VERIFY", "reason": "ZONING_DISTRICT_MISSING"}
    if not str(project_goal or "").strip():
        return {"status": "VERIFY", "reason": "PROJECT_GOAL_MISSING"}

    items = list(requirements or [])
    if not items:
        return {"status": "VERIFY", "reason": "NO_PROJECT_RULE_EVIDENCE"}

    source = dict(source or {})
    return {
        "status": "PROJECT_RULES_CANDIDATE",
        "municipality": municipality,
        "zoning_district": zoning_district,
        "project_goal": project_goal,
        "requirements": items,
        "source": source,
        "authoritative": source.get("authoritative") is True,
        "legal_control_confirmed": source.get("legal_control_confirmed") is True,
    }


def evaluate_dynamic_project_applicability(
    candidate: dict[str, Any] | None,
    *,
    property_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a dynamic candidate without silently promoting its source."""
    if not candidate or candidate.get("status") != "PROJECT_RULES_CANDIDATE":
        return {
            "status": "VERIFY",
            "applicable": False,
            "promotable": False,
            "reason": "PROJECT_RULE_CANDIDATE_NOT_AVAILABLE",
        }

    if candidate.get("authoritative") is not True:
        return {
            "status": "VERIFY",
            "applicable": False,
            "promotable": False,
            "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED",
        }

    if candidate.get("legal_control_confirmed") is not True:
        return {
            "status": "VERIFY",
            "applicable": False,
            "promotable": False,
            "reason": "LEGAL_CONTROL_NOT_CONFIRMED",
        }

    evaluation = evaluate_project_rule_applicability(
        municipality=candidate["municipality"],
        zoning_district=candidate["zoning_district"],
        project_goal=candidate["project_goal"],
        property_resolution=property_resolution,
        project_requirements=candidate["requirements"],
    )

    return {
        "status": evaluation["status"],
        "applicable": bool(evaluation["applicable"]),
        "promotable": True,
        "reason": evaluation["reason"],
        "evaluation": evaluation,
        "source": candidate["source"],
    }
