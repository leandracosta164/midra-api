from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"
COVERAGE = ROOT / "app" / "services" / "municipality_coverage.py"
APPLICABILITY = ROOT / "app" / "services" / "rule_applicability.py"


def fail(message: str) -> None:
    raise RuntimeError(message + "\nNo file was changed.")


def run_compile(path: Path) -> None:
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
    print("MIDRA rule applicability layer")
    print("==============================================")
    print()

    for path in (MAIN, COVERAGE, APPLICABILITY):
        if not path.exists():
            fail(f"Missing file: {path}")

    main_text = MAIN.read_text(encoding="utf-8")

    if "evaluate_project_rule_applicability" in main_text:
        print("Rule applicability integration is already installed.")
        print("No file was changed.")
        return

    import_marker = (
        "from app.services.municipality_coverage import "
        "build_municipality_coverage"
    )

    if import_marker not in main_text:
        fail("Could not find the municipality coverage import in main.py.")

    coverage_marker = '''    zoning_intelligence["coverage"] = (
        build_municipality_coverage(
            municipality=municipality,
            zoning_intelligence=zoning_intelligence,
            zoning_resolution=zoning_resolution,
            project_goal=payload.project_goal,
        )
    )
'''

    if coverage_marker not in main_text:
        fail(
            "Could not find the installed municipality coverage "
            "integration block in main.py."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_backup = MAIN.with_name(
        f"main.py.before-rule-applicability-{stamp}"
    )
    coverage_backup = COVERAGE.with_name(
        f"municipality_coverage.py.before-rule-applicability-{stamp}"
    )

    shutil.copy2(MAIN, main_backup)
    shutil.copy2(COVERAGE, coverage_backup)

    try:
        updated = main_text.replace(
            import_marker,
            import_marker
            + "\n"
            + "from app.services.rule_applicability import "
            "evaluate_project_rule_applicability",
            1,
        )

        applicability_block = coverage_marker + '''
    # ========================================================
    # STEP 3C — PROJECT RULE APPLICABILITY
    # ========================================================

    zoning_intelligence["project_rule_applicability"] = (
        evaluate_project_rule_applicability(
            municipality=municipality,
            zoning_district=zoning_intelligence.get(
                "zoning_district"
            ),
            project_goal=payload.project_goal,
            zoning_resolution=zoning_resolution,
            property_resolution=property_resolution,
            project_requirements=zoning_intelligence.get(
                "project_requirements"
            ),
        )
    )
'''

        updated = updated.replace(
            coverage_marker,
            applicability_block,
            1,
        )

        MAIN.write_text(updated, encoding="utf-8")

        run_compile(APPLICABILITY)
        run_compile(COVERAGE)
        run_compile(MAIN)

    except Exception:
        shutil.copy2(main_backup, MAIN)
        shutil.copy2(coverage_backup, COVERAGE)
        raise

    print("Backups:")
    print(" ", main_backup)
    print(" ", coverage_backup)
    print("Added:", APPLICABILITY)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Rule applicability layer is installed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
