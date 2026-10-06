from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"

IMPORT_LINE = "from app.services.municipality_identity import resolve_municipality_identity"
COVERAGE_IMPORT = "from app.services.municipality_coverage import build_municipality_coverage"

IDENTITY_BLOCK = '    # ========================================================\n    # STEP 3B — MUNICIPALITY IDENTITY\n    # ========================================================\n    #\n    # Stage A establishes statewide municipality identity only.\n    # It does not determine zoning, source verification, or rules.\n    # ========================================================\n    municipality_identity = resolve_municipality_identity(\n        municipality=municipality,\n        county=(\n            (property_resolution or {}).get("county")\n            or zoning_resolution.get("county")\n        ),\n        state=(\n            (property_resolution or {}).get("state")\n            or "New Jersey"\n        ),\n        municipality_code=(\n            ((property_resolution or {}).get("parcel") or {}).get(\n                "municipality_code"\n            )\n        ),\n    )\n\n'


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
    print("MIDRA Stage A — API integration")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing required file: {MAIN}")

    text = MAIN.read_text(encoding="utf-8")

    if IMPORT_LINE in text:
        raise RuntimeError(
            "Stage A identity import is already present. No changes were made."
        )

    marker = "    # STEP 3B — MUNICIPALITY COVERAGE"

    if marker not in text:
        raise RuntimeError(
            "Could not find the existing STEP 3B municipality coverage marker. "
            "No changes were made."
        )

    if COVERAGE_IMPORT not in text:
        raise RuntimeError(
            "Could not find the existing municipality coverage import. "
            "No changes were made."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(f"main.py.before-stage-a-integration-{stamp}")
    shutil.copy2(MAIN, backup)

    try:
        text = text.replace(
            COVERAGE_IMPORT,
            IMPORT_LINE + "\n" + COVERAGE_IMPORT,
            1,
        )
        text = text.replace(
            marker,
            IDENTITY_BLOCK + marker,
            1,
        )

        MAIN.write_text(text, encoding="utf-8")
        compile_file(MAIN)
    except Exception:
        shutil.copy2(backup, MAIN)
        raise

    print("Backup:", backup)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Stage A municipality identity is integrated into main.py.")
    print("Existing zoning, coverage, and applicability logic was not replaced.")
    print("The integration occurs before the existing municipality coverage step.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
