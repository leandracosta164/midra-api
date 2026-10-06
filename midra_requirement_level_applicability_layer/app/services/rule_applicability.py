from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip().lower()


def _requirement_label(item: dict[str, Any]) -> str:
    return str(item.get("requirement") or "Unnamed requirement").strip()


def _is_municipal_facility(property_resolution: dict[str, Any] | None) -> bool:
    parcel = (property_resolution or {}).get("parcel") or {}
    building = _text(parcel.get("building_description"))
    property_class = _text(parcel.get("property_class"))
    return (
        "municipal" in building
        or property_class in {"15c", "15c municipal", "15c - municipal"}
    )


def evaluate_requirement_applicability(
    *,
    municipality: str | None,
    zoning_district: str | None,
    project_goal: str | None,
    requirement: dict[str, Any],
    zoning_resolution: dict[str, Any] | None = None,
    property_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one returned project requirement conservatively.

    This function intentionally distinguishes:
      APPLICABLE       - current property/project evidence supports use.
      NOT_APPLICABLE   - current property/project evidence conflicts with
                         the requirement's stated prerequisite.
      VERIFY           - the rule exists, but the available evidence is not
                         sufficient to make a property-specific determination.
    """

    municipality_key = _text(municipality)
    district_key = str(zoning_district or "").strip().upper()
    goal_key = _text(project_goal)
    label = _requirement_label(requirement)

    text = " ".join(
        _text(requirement.get(key))
        for key in ("requirement", "value", "basis", "applies_to")
    )

    is_pool = goal_key in {"pool", "swimming pool", "swimming pools"}
    is_howell_hd4 = (
        municipality_key in {"howell township", "howell twp", "howell"}
        and district_key == "HD-4"
    )
    is_marlboro_cf = (
        municipality_key in {"marlboro township", "marlboro twp", "marlboro"}
        and district_key == "CF"
    )

    # Explicit negative rule for the Marlboro residential-pool prerequisite.
    if (
        is_marlboro_cf
        and is_pool
        and (
            "residential building" in text
            or "private permanent residential pool" in text
        )
        and _is_municipal_facility(property_resolution)
    ):
        return {
            "requirement": label,
            "status": "NOT_APPLICABLE",
            "applicable": False,
            "reason": (
                "The requirement is for a private permanent residential "
                "pool, while the resolved parcel is identified as a "
                "municipal facility."
            ),
        }

    # Explicit positive rules for the verified Howell HD-4 pool rule set.
    # These are deliberately limited to the existing Howell project rules.
    if is_howell_hd4 and is_pool:
        return {
            "requirement": label,
            "status": "APPLICABLE",
            "applicable": True,
            "reason": (
                "The requirement was selected from Howell Township's "
                "verified HD-4 pool project rules."
            ),
        }

    return {
        "requirement": label,
        "status": "VERIFY",
        "applicable": False,
        "reason": (
            "The rule is available, but the current property-specific "
            "evidence is insufficient to determine individual applicability."
        ),
    }


def evaluate_project_rule_applicability(
    *,
    municipality: str | None,
    zoning_district: str | None,
    project_goal: str | None,
    zoning_resolution: dict[str, Any] | None = None,
    property_resolution: dict[str, Any] | None = None,
    project_requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return project-level status plus individual requirement decisions."""

    requirements = list(project_requirements or [])

    if not requirements:
        return {
            "status": "NO_RULES_AVAILABLE",
            "applicable": False,
            "reason": (
                "No project-specific rules are currently available "
                "for the resolved municipality/district/project."
            ),
            "evaluated_requirement_count": 0,
            "requirements": [],
        }

    evaluations = [
        evaluate_requirement_applicability(
            municipality=municipality,
            zoning_district=zoning_district,
            project_goal=project_goal,
            requirement=item,
            zoning_resolution=zoning_resolution,
            property_resolution=property_resolution,
        )
        for item in requirements
    ]

    statuses = {item["status"] for item in evaluations}

    if statuses == {"APPLICABLE"}:
        status = "APPLICABLE"
        applicable = True
        reason = (
            "All returned project requirements are supported as applicable "
            "for the resolved property and project."
        )
    elif statuses == {"NOT_APPLICABLE"}:
        status = "NOT_APPLICABLE"
        applicable = False
        reason = (
            "All returned project requirements are not applicable to the "
            "resolved property and project."
        )
    elif "APPLICABLE" in statuses:
        status = "PARTIALLY_APPLICABLE"
        applicable = True
        reason = (
            "Some project requirements are applicable, while other "
            "requirements require verification or are not applicable."
        )
    else:
        status = "VERIFY"
        applicable = False
        reason = (
            "Project-rule applicability could not be fully determined "
            "from the currently resolved property evidence."
        )

    return {
        "status": status,
        "applicable": applicable,
        "reason": reason,
        "evaluated_requirement_count": len(evaluations),
        "requirements": evaluations,
    }


# Backward-compatible alias for callers that may use the shorter name.
build_rule_applicability = evaluate_project_rule_applicability
