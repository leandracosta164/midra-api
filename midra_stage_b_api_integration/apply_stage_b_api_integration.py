from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"

IMPORT_LINE = (
    "from app.services.municipality_source_registry "
    "import resolve_municipality_source"
)
IDENTITY_IMPORT = (
    "from app.services.municipality_identity "
    "import resolve_municipality_identity"
)

IDENTITY_MARKER = "    # STEP 3B — MUNICIPALITY IDENTITY"
COVERAGE_MARKER = "    # STEP 3B — MUNICIPALITY COVERAGE"

SOURCE_BLOCK = '''    # ========================================================
    # STEP 3B — MUNICIPALITY SOURCE REGISTRY
    # ========================================================
    #
    # Stage B identifies official municipal zoning sources only.
    # It does not resolve parcel zoning and does not establish
    # project-rule applicability.
    # ========================================================
    municipality_source_registry = (
        resolve_municipality_source(municipality)
    )

'''

RETURN_MARKER = '''        "municipality_identity": (
            municipality_identity
        ),

        "zoning_resolution": ('''

RETURN_REPLACEMENT = '''        "municipality_identity": (
            municipality_identity
        ),

        "municipality_source_registry": (
            municipality_source_registry
        ),

        "zoning_resolution": ('''


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
    print("MIDRA Stage B — API integration")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing required file: {MAIN}")

    text = MAIN.read_text(encoding="utf-8")

    if IMPORT_LINE in text:
        raise RuntimeError(
            "Stage B API import is already present. No changes were made."
        )

    if IDENTITY_IMPORT not in text:
        raise RuntimeError(
            "Stage A municipality identity import was not found. "
            "Stage B integration requires the verified Stage A integration."
        )

    if IDENTITY_MARKER not in text:
        raise RuntimeError(
            "Could not find the verified Stage A identity section. "
            "No changes were made."
        )

    if COVERAGE_MARKER not in text:
        raise RuntimeError(
            "Could not find the existing municipality coverage section. "
            "No changes were made."
        )

    if RETURN_MARKER not in text:
        raise RuntimeError(
            "Could not find the verified Stage A response block. "
            "No changes were made."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-b-integration-{stamp}"
    )
    shutil.copy2(MAIN, backup)

    try:
        text = text.replace(
            IDENTITY_IMPORT,
            IDENTITY_IMPORT + "\n" + IMPORT_LINE,
            1,
        )

        text = text.replace(
            COVERAGE_MARKER,
            SOURCE_BLOCK + COVERAGE_MARKER,
            1,
        )

        text = text.replace(
            RETURN_MARKER,
            RETURN_REPLACEMENT,
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
    print("Stage B municipality source registry is integrated into main.py.")
    print("Stage B source identification is exposed separately in the API response.")
    print("Existing zoning, coverage, and applicability logic was not replaced.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
