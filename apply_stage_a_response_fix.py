from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"

OLD = """        "property_resolution": (
            property_resolution
        ),

        "zoning_resolution": (
            zoning_resolution
        ),"""

NEW = """        "property_resolution": (
            property_resolution
        ),

        "municipality_identity": (
            municipality_identity
        ),

        "zoning_resolution": (
            zoning_resolution
        ),"""


def compile_file(path: Path) -> None:
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Syntax check failed for {path}.\\n"
            f"{result.stdout}{result.stderr}"
        )


def main() -> None:
    print("==============================================")
    print("MIDRA Stage A — response integration correction")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing required file: {MAIN}")

    text = MAIN.read_text(encoding="utf-8")

    if '"municipality_identity": (' in text:
        raise RuntimeError(
            "municipality_identity is already present in the response. "
            "No changes were made."
        )

    if OLD not in text:
        raise RuntimeError(
            "Could not find the expected STEP 9 response block. "
            "No changes were made."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-a-response-fix-{stamp}"
    )
    shutil.copy2(MAIN, backup)

    try:
        updated = text.replace(OLD, NEW, 1)
        MAIN.write_text(updated, encoding="utf-8")
        compile_file(MAIN)
    except Exception:
        shutil.copy2(backup, MAIN)
        raise

    print("Backup:", backup)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Stage A municipality_identity is now included in the API response.")
    print("No zoning, coverage, or applicability logic was changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
