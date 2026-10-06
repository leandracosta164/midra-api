from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"
TARGET = ROOT / "app" / "services" / "rule_applicability.py"

CORRECTED_SOURCE = 'from __future__ import annotations\n\nfrom typing import Any\n\n\ndef _text(value: object) -> str:\n    return str(value or "").strip().lower()\n\n\ndef _requirement_label(item: dict[str, Any]) -> str:\n    return str(item.get("requirement") or "Unnamed requirement").strip()\n\n\ndef _is_municipal_facility(\n    property_resolution: dict[str, Any] | None,\n) -> bool:\n    parcel = (property_resolution or {}).get("parcel") or {}\n    building = _text(parcel.get("building_description"))\n    property_class = _text(parcel.get("property_class"))\n    return (\n        "municipal" in building\n        or property_class in {"15c", "15c municipal", "15c - municipal"}\n    )\n\n\ndef _explicit_property_use(\n    property_resolution: dict[str, Any] | None,\n) -> str:\n    parcel = (property_resolution or {}).get("parcel") or {}\n    for key in (\n        "property_use_description",\n        "property_class_description",\n        "property_type",\n        "land_use_description",\n    ):\n        value = _text(parcel.get(key))\n        if value:\n            return value\n    return ""\n\n\ndef _is_explicitly_commercial(\n    property_resolution: dict[str, Any] | None,\n) -> bool:\n    """Only classify as commercial when the source explicitly says so.\n\n    Numeric tax/property-class codes such as 4A are intentionally not\n    interpreted here because the resolver does not provide their semantic\n    meaning.\n    """\n    use = _explicit_property_use(property_resolution)\n    return (\n        "commercial" in use\n        or use in {\n            "commercial property",\n            "commercial parcel",\n            "commercial use",\n        }\n    )\n\n\ndef _is_explicitly_residential(\n    property_resolution: dict[str, Any] | None,\n) -> bool:\n    use = _explicit_property_use(property_resolution)\n    return (\n        "residential" in use\n        or use in {\n            "residential property",\n            "residential parcel",\n            "residential use",\n        }\n    )\n\n\ndef evaluate_requirement_applicability(\n    *,\n    municipality: str | None,\n    zoning_district: str | None,\n    project_goal: str | None,\n    requirement: dict[str, Any],\n    zoning_resolution: dict[str, Any] | None = None,\n    property_resolution: dict[str, Any] | None = None,\n) -> dict[str, Any]:\n    """Evaluate one project requirement conservatively."""\n\n    municipality_key = _text(municipality)\n    district_key = str(zoning_district or "").strip().upper()\n    goal_key = _text(project_goal)\n    label = _requirement_label(requirement)\n\n    text = " ".join(\n        _text(requirement.get(key))\n        for key in ("requirement", "value", "basis", "applies_to")\n    )\n\n    is_pool = goal_key in {\n        "pool",\n        "swimming pool",\n        "swimming pools",\n    }\n\n    is_howell_hd4 = (\n        municipality_key in {\n            "howell township",\n            "howell twp",\n            "howell",\n        }\n        and district_key == "HD-4"\n    )\n\n    is_marlboro_cf = (\n        municipality_key in {\n            "marlboro township",\n            "marlboro twp",\n            "marlboro",\n        }\n        and district_key == "CF"\n    )\n\n    if (\n        is_marlboro_cf\n        and is_pool\n        and (\n            "residential building" in text\n            or "private permanent residential pool" in text\n        )\n        and _is_municipal_facility(property_resolution)\n    ):\n        return {\n            "requirement": label,\n            "status": "NOT_APPLICABLE",\n            "applicable": False,\n            "reason": (\n                "The requirement is for a private permanent residential "\n                "pool, while the resolved parcel is identified as a "\n                "municipal facility."\n            ),\n        }\n\n    if (\n        is_pool\n        and (\n            "commercial property" in text\n            or "commercial property improvements" in text\n            or "commercial property improvement" in text\n        )\n    ):\n        if _is_explicitly_commercial(property_resolution):\n            return {\n                "requirement": label,\n                "status": "APPLICABLE",\n                "applicable": True,\n                "reason": (\n                    "The requirement expressly applies to commercial "\n                    "property improvements and the resolved property "\n                    "evidence explicitly identifies the parcel as commercial."\n                ),\n            }\n\n        if _is_explicitly_residential(property_resolution):\n            return {\n                "requirement": label,\n                "status": "NOT_APPLICABLE",\n                "applicable": False,\n                "reason": (\n                    "The requirement expressly applies to commercial "\n                    "property improvements, while the resolved property "\n                    "evidence explicitly identifies the parcel as residential."\n                ),\n            }\n\n        return {\n            "requirement": label,\n            "status": "VERIFY",\n            "applicable": False,\n            "reason": (\n                "The requirement is specific to commercial property "\n                "improvements, but the authoritative property resolver "\n                "does not provide an explicit commercial/residential "\n                "semantic classification. Numeric property-class codes "\n                "are not interpreted as legal land-use classifications."\n            ),\n        }\n\n    if is_howell_hd4 and is_pool:\n        return {\n            "requirement": label,\n            "status": "APPLICABLE",\n            "applicable": True,\n            "reason": (\n                "The requirement was selected from Howell Township\'s "\n                "verified HD-4 pool project rules."\n            ),\n        }\n\n    return {\n        "requirement": label,\n        "status": "VERIFY",\n        "applicable": False,\n        "reason": (\n            "The rule is available, but the current property-specific "\n            "evidence is insufficient to determine individual applicability."\n        ),\n    }\n\n\ndef evaluate_project_rule_applicability(\n    *,\n    municipality: str | None,\n    zoning_district: str | None,\n    project_goal: str | None,\n    zoning_resolution: dict[str, Any] | None = None,\n    property_resolution: dict[str, Any] | None = None,\n    project_requirements: list[dict[str, Any]] | None = None,\n) -> dict[str, Any]:\n    """Return project status plus individual requirement decisions."""\n\n    requirements = list(project_requirements or [])\n\n    if not requirements:\n        return {\n            "status": "NO_RULES_AVAILABLE",\n            "applicable": False,\n            "reason": (\n                "No project-specific rules are currently available "\n                "for the resolved municipality/district/project."\n            ),\n            "evaluated_requirement_count": 0,\n            "requirements": [],\n        }\n\n    evaluations = [\n        evaluate_requirement_applicability(\n            municipality=municipality,\n            zoning_district=zoning_district,\n            project_goal=project_goal,\n            requirement=item,\n            zoning_resolution=zoning_resolution,\n            property_resolution=property_resolution,\n        )\n        for item in requirements\n    ]\n\n    statuses = {item["status"] for item in evaluations}\n\n    if statuses == {"APPLICABLE"}:\n        status, applicable = "APPLICABLE", True\n        reason = (\n            "All returned project requirements are supported as applicable "\n            "for the resolved property and project."\n        )\n    elif statuses == {"NOT_APPLICABLE"}:\n        status, applicable = "NOT_APPLICABLE", False\n        reason = (\n            "All returned project requirements are not applicable to the "\n            "resolved property and project."\n        )\n    elif "APPLICABLE" in statuses:\n        status, applicable = "PARTIALLY_APPLICABLE", True\n        reason = (\n            "Some project requirements are applicable, while other "\n            "requirements require verification or are not applicable."\n        )\n    else:\n        status, applicable = "VERIFY", False\n        reason = (\n            "Project-rule applicability could not be fully determined "\n            "from the currently resolved property evidence."\n        )\n\n    return {\n        "status": status,\n        "applicable": applicable,\n        "reason": reason,\n        "evaluated_requirement_count": len(evaluations),\n        "requirements": evaluations,\n    }\n\n\nbuild_rule_applicability = evaluate_project_rule_applicability\n'


def compile_file(path: Path) -> None:
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Syntax check failed for {path}.\n"
            f"{result.stdout}{result.stderr}"
        )


def main() -> None:
    print("==============================================")
    print("MIDRA property-classification safety correction")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing required file: {MAIN}")

    if not TARGET.exists():
        raise RuntimeError(f"Missing required file: {TARGET}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"rule_applicability.py.before-property-classification-safety-{stamp}"
    )

    shutil.copy2(TARGET, backup)

    try:
        TARGET.write_text(CORRECTED_SOURCE, encoding="utf-8")
        compile_file(TARGET)
        compile_file(MAIN)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Updated:", TARGET)
    print()
    print("SUCCESS")
    print("Numeric property-class codes are no longer interpreted as commercial.")
    print("Explicit commercial/residential semantic evidence is required.")
    print("Howell HD-4 pool rules remain individually supported.")
    print("Marlboro municipal-facility safeguard remains intact.")
    print("Unknown property classification remains VERIFY.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
