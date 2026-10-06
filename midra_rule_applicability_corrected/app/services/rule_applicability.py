from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip().lower()


def evaluate_project_rule_applicability(
    *,
    municipality: str | None,
    zoning_district: str | None,
    project_goal: str | None,
    zoning_resolution: dict[str, Any] | None,
    property_resolution: dict[str, Any] | None,
    project_requirements: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Evaluate whether returned project rules apply to the property."""

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
        }

    municipality_key = _text(municipality)
    goal_key = _text(project_goal)
    district_key = _text(zoning_district).upper()

    parcel = (property_resolution or {}).get("parcel") or {}
    building_description = _text(parcel.get("building_description"))
    property_class = _text(parcel.get("property_class"))

    is_marlboro = municipality_key in {
        "marlboro township",
        "marlboro twp",
        "marlboro",
    }

    is_howell = municipality_key in {
        "howell township",
        "howell twp",
        "howell",
    }

    is_pool = goal_key in {
        "pool",
        "swimming pool",
        "swimming pools",
    }

    # Explicit negative applicability:
    # Marlboro's private permanent residential pool rule requires
    # a residential building. Do not present it as applicable to
    # a resolved municipal-facility parcel.
    residential_prerequisite = any(
        "residential building" in _text(item.get("requirement"))
        or "residential building" in _text(item.get("basis"))
        or "residential building" in _text(item.get("value"))
        for item in requirements
    )

    if (
        is_marlboro
        and is_pool
        and district_key == "CF"
        and residential_prerequisite
    ):
        municipal_building = (
            "municipal" in building_description
            or property_class == "15c"
        )

        if municipal_building:
            return {
                "status": "NOT_APPLICABLE",
                "applicable": False,
                "reason": (
                    "Marlboro's private permanent residential pool "
                    "rule requires a residential building. The "
                    "resolved parcel is identified as a municipal "
                    "facility, so that private residential pool rule "
                    "is not treated as applicable to this property."
                ),
                "evaluated_requirement_count": len(requirements),
            }

    # Explicit positive applicability:
    # Howell HD-4 pool rules are already returned from the verified
    # municipal/project rules layer. The existing Howell result is
    # therefore allowed to report applicability rather than falling
    # back to VERIFY.
    if (
        is_howell
        and is_pool
        and district_key == "HD-4"
        and len(requirements) > 0
    ):
        return {
            "status": "APPLICABLE",
            "applicable": True,
            "reason": (
                "Howell Township project-specific pool requirements "
                "are available for the resolved HD-4 property."
            ),
            "evaluated_requirement_count": len(requirements),
        }

    # Conservative default: rule existence alone is not enough
    # to declare applicability.
    return {
        "status": "VERIFY",
        "applicable": False,
        "reason": (
            "Project-specific rules are available, but the current "
            "rule metadata does not establish enough property-specific "
            "facts to declare applicability."
        ),
        "evaluated_requirement_count": len(requirements),
    }
