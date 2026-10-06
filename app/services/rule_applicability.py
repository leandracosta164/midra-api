from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip().lower()


def _requirement_label(item: dict[str, Any]) -> str:
    return str(item.get("requirement") or "Unnamed requirement").strip()


def _is_municipal_facility(
    property_resolution: dict[str, Any] | None,
) -> bool:
    parcel = (property_resolution or {}).get("parcel") or {}
    building = _text(parcel.get("building_description"))
    property_class = _text(parcel.get("property_class"))

    # Building-description values are public-record descriptors and may
    # contain arbitrary names or labels. Do not treat a substring such as
    # "municipal" as sufficient semantic proof of municipal ownership/use.
    # Preserve the existing explicit municipal-building record while making
    # the classification conservative.
    explicit_municipal_building = building in {
        "municipal bldg",
        "municipal building",
    }

    return (
        explicit_municipal_building
        or property_class in {"15c", "15c municipal", "15c - municipal"}
    )


def _explicit_property_use(
    property_resolution: dict[str, Any] | None,
) -> str:
    parcel = (property_resolution or {}).get("parcel") or {}
    for key in (
        "property_use_description",
        "property_class_description",
        "property_type",
        "land_use_description",
    ):
        value = _text(parcel.get(key))
        if value:
            return value
    return ""


def _is_explicitly_commercial(
    property_resolution: dict[str, Any] | None,
) -> bool:
    """Only classify as commercial when the source explicitly says so."""
    use = _explicit_property_use(property_resolution)
    return (
        "commercial" in use
        or use in {
            "commercial property",
            "commercial parcel",
            "commercial use",
        }
    )


def _is_explicitly_residential(
    property_resolution: dict[str, Any] | None,
) -> bool:
    use = _explicit_property_use(property_resolution)
    return (
        "residential" in use
        or use in {
            "residential property",
            "residential parcel",
            "residential use",
        }
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
    """Evaluate one project requirement conservatively."""

    label = _requirement_label(requirement)

    text = " ".join(
        _text(requirement.get(key))
        for key in ("requirement", "value", "basis", "applies_to")
    )

    goal_key = _text(project_goal)

    is_pool = goal_key in {
        "pool",
        "swimming pool",
        "swimming pools",
    }

    if (
        is_pool
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

    registry_applicability = _text(
        requirement.get("registry_applicability")
    )

    if registry_applicability == "applicable":
        return {
            "requirement": label,
            "status": "APPLICABLE",
            "applicable": True,
            "reason": (
                "The requirement is explicitly marked applicable "
                "by the verified municipal/district/project rule registry."
            ),
        }

    if registry_applicability == "not_applicable":
        return {
            "requirement": label,
            "status": "NOT_APPLICABLE",
            "applicable": False,
            "reason": (
                "The requirement is explicitly marked not applicable "
                "by the verified municipal/district/project rule registry."
            ),
        }
    if (
        is_pool
        and (
            "commercial property" in text
            or "commercial property improvements" in text
            or "commercial property improvement" in text
        )
    ):
        if _is_explicitly_commercial(property_resolution):
            return {
                "requirement": label,
                "status": "APPLICABLE",
                "applicable": True,
                "reason": (
                    "The requirement expressly applies to commercial "
                    "property improvements and the resolved property "
                    "evidence explicitly identifies the parcel as commercial."
                ),
            }

        if _is_explicitly_residential(property_resolution):
            return {
                "requirement": label,
                "status": "NOT_APPLICABLE",
                "applicable": False,
                "reason": (
                    "The requirement expressly applies to commercial "
                    "property improvements, while the resolved property "
                    "evidence explicitly identifies the parcel as residential."
                ),
            }

        return {
            "requirement": label,
            "status": "VERIFY",
            "applicable": False,
            "reason": (
                "The requirement is specific to commercial property "
                "improvements, but the authoritative property resolver "
                "does not provide an explicit commercial/residential "
                "semantic classification. Numeric property-class codes "
                "are not interpreted as legal land-use classifications."
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
    """Return project status plus individual requirement decisions."""

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
        status, applicable = "APPLICABLE", True
        reason = (
            "All returned project requirements are supported as applicable "
            "for the resolved property and project."
        )
    elif statuses == {"NOT_APPLICABLE"}:
        status, applicable = "NOT_APPLICABLE", False
        reason = (
            "All returned project requirements are not applicable to the "
            "resolved property and project."
        )
    elif "APPLICABLE" in statuses:
        status, applicable = "PARTIALLY_APPLICABLE", True
        reason = (
            "Some project requirements are applicable, while other "
            "requirements require verification or are not applicable."
        )
    else:
        status, applicable = "VERIFY", False
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


build_rule_applicability = evaluate_project_rule_applicability



