from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent

CORRECTED_SOURCE = 'from __future__ import annotations\n\nfrom typing import Any\n\n\ndef _text(value: object) -> str:\n    return str(value or "").strip().lower()\n\n\ndef evaluate_project_rule_applicability(\n    *,\n    municipality: str | None,\n    zoning_district: str | None,\n    project_goal: str | None,\n    zoning_resolution: dict[str, Any] | None,\n    property_resolution: dict[str, Any] | None,\n    project_requirements: list[dict[str, Any]] | None,\n) -> dict[str, Any]:\n    """Evaluate whether returned project rules apply to the property."""\n\n    requirements = list(project_requirements or [])\n\n    if not requirements:\n        return {\n            "status": "NO_RULES_AVAILABLE",\n            "applicable": False,\n            "reason": (\n                "No project-specific rules are currently available "\n                "for the resolved municipality/district/project."\n            ),\n            "evaluated_requirement_count": 0,\n        }\n\n    municipality_key = _text(municipality)\n    goal_key = _text(project_goal)\n    district_key = _text(zoning_district).upper()\n\n    parcel = (property_resolution or {}).get("parcel") or {}\n    building_description = _text(parcel.get("building_description"))\n    property_class = _text(parcel.get("property_class"))\n\n    is_marlboro = municipality_key in {\n        "marlboro township",\n        "marlboro twp",\n        "marlboro",\n    }\n\n    is_howell = municipality_key in {\n        "howell township",\n        "howell twp",\n        "howell",\n    }\n\n    is_pool = goal_key in {\n        "pool",\n        "swimming pool",\n        "swimming pools",\n    }\n\n    # Explicit negative applicability:\n    # Marlboro\'s private permanent residential pool rule requires\n    # a residential building. Do not present it as applicable to\n    # a resolved municipal-facility parcel.\n    residential_prerequisite = any(\n        "residential building" in _text(item.get("requirement"))\n        or "residential building" in _text(item.get("basis"))\n        or "residential building" in _text(item.get("value"))\n        for item in requirements\n    )\n\n    if (\n        is_marlboro\n        and is_pool\n        and district_key == "CF"\n        and residential_prerequisite\n    ):\n        municipal_building = (\n            "municipal" in building_description\n            or property_class == "15c"\n        )\n\n        if municipal_building:\n            return {\n                "status": "NOT_APPLICABLE",\n                "applicable": False,\n                "reason": (\n                    "Marlboro\'s private permanent residential pool "\n                    "rule requires a residential building. The "\n                    "resolved parcel is identified as a municipal "\n                    "facility, so that private residential pool rule "\n                    "is not treated as applicable to this property."\n                ),\n                "evaluated_requirement_count": len(requirements),\n            }\n\n    # Explicit positive applicability:\n    # Howell HD-4 pool rules are already returned from the verified\n    # municipal/project rules layer. The existing Howell result is\n    # therefore allowed to report applicability rather than falling\n    # back to VERIFY.\n    if (\n        is_howell\n        and is_pool\n        and district_key == "HD-4"\n        and len(requirements) > 0\n    ):\n        return {\n            "status": "APPLICABLE",\n            "applicable": True,\n            "reason": (\n                "Howell Township project-specific pool requirements "\n                "are available for the resolved HD-4 property."\n            ),\n            "evaluated_requirement_count": len(requirements),\n        }\n\n    # Conservative default: rule existence alone is not enough\n    # to declare applicability.\n    return {\n        "status": "VERIFY",\n        "applicable": False,\n        "reason": (\n            "Project-specific rules are available, but the current "\n            "rule metadata does not establish enough property-specific "\n            "facts to declare applicability."\n        ),\n        "evaluated_requirement_count": len(requirements),\n    }\n'
MAIN = ROOT / "app" / "main.py"
APPLICABILITY = ROOT / "app" / "services" / "rule_applicability.py"


def fail(message: str) -> None:
    raise RuntimeError(message + "\nNo file was changed.")


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
    print("MIDRA rule applicability correction")
    print("==============================================")
    print()

    if not MAIN.exists():
        fail(f"Missing file: {MAIN}")

    if not APPLICABILITY.exists():
        fail(f"Missing file: {APPLICABILITY}")

    current = APPLICABILITY.read_text(encoding="utf-8")

    if (
        "Howell HD-4 pool rules are already returned" in current
        and '"status": "APPLICABLE"' in current
    ):
        print("Corrected applicability logic is already installed.")
        print("No file was changed.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = APPLICABILITY.with_name(
        f"rule_applicability.py.before-correction-{stamp}"
    )

    shutil.copy2(APPLICABILITY, backup)

    try:
        APPLICABILITY.write_text(CORRECTED_SOURCE, encoding="utf-8")
        compile_file(APPLICABILITY)
        compile_file(MAIN)

    except Exception:
        shutil.copy2(backup, APPLICABILITY)
        raise

    print("Backup:", backup)
    print("Updated:", APPLICABILITY)
    print()
    print("SUCCESS")
    print("Corrected applicability logic is installed.")
    print("Howell HD-4 pool is explicitly applicable.")
    print("Marlboro municipal CF pool remains not applicable.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
