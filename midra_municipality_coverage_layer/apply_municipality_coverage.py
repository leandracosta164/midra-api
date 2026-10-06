from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"
COVERAGE = ROOT / "app" / "services" / "municipality_coverage.py"

IMPORT_MARKER = (
    "from app.services.zoning_intelligence import get_zoning_intelligence"
)

IMPORT_REPLACEMENT = (
    "from app.services.zoning_intelligence import get_zoning_intelligence\n"
    "from app.services.municipality_coverage import "
    "build_municipality_coverage"
)

MERGE_MARKER = """    zoning_intelligence = (
        _merge_property_specific_zoning(
            zoning_intelligence=zoning_intelligence,
            zoning_resolution=zoning_resolution,
        )
    )
"""

MERGE_REPLACEMENT = MERGE_MARKER + """
    # ========================================================
    # STEP 3B — MUNICIPALITY COVERAGE
    # ========================================================
    #
    # Coverage is derived from the same municipality registry,
    # property-specific zoning result, and district/project rules
    # used by the intelligence engine.
    #
    # It is metadata only: it does not change zoning decisions.
    # ========================================================

    zoning_intelligence["coverage"] = (
        build_municipality_coverage(
            municipality=municipality,
            zoning_intelligence=zoning_intelligence,
            zoning_resolution=zoning_resolution,
            project_goal=payload.project_goal,
        )
    )

"""


def fail(message: str) -> None:
    raise RuntimeError(message + "\nNo file was changed.")


def main() -> None:
    print("==============================================")
    print("MIDRA municipality coverage layer")
    print("==============================================")
    print()

    if not MAIN.exists():
        fail(f"Missing file: {MAIN}")

    if not COVERAGE.exists():
        fail(f"Missing file: {COVERAGE}")

    text = MAIN.read_text(encoding="utf-8")

    # Idempotence.
    if "build_municipality_coverage" in text:
        print("Coverage integration is already installed.")
        print("No file was changed.")
        return

    if IMPORT_MARKER not in text:
        fail(
            "Could not find the expected zoning_intelligence import "
            "in app/main.py."
        )

    if MERGE_MARKER not in text:
        fail(
            "Could not find the expected STEP 3A zoning merge block "
            "in app/main.py."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    main_backup = MAIN.with_name(
        f"main.py.before-coverage-{stamp}"
    )

    shutil.copy2(MAIN, main_backup)

    try:
        updated = text.replace(
            IMPORT_MARKER,
            IMPORT_REPLACEMENT,
            1,
        )

        updated = updated.replace(
            MERGE_MARKER,
            MERGE_REPLACEMENT,
            1,
        )

        MAIN.write_text(
            updated,
            encoding="utf-8",
        )

        for path in (
            COVERAGE,
            MAIN,
        ):
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "py_compile",
                    str(path),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Syntax check failed for {path}.\n"
                    f"{result.stdout}{result.stderr}"
                )

    except Exception:
        shutil.copy2(
            main_backup,
            MAIN,
        )
        raise

    print("Backup:", main_backup)
    print("Added:", COVERAGE)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Municipality coverage metadata is installed.")
    print("Both Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
