from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"


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
    print("MIDRA Stage C — API resolution bridge fix")
    print("==============================================")
    print()

    original = MAIN.read_text(encoding="utf-8")

    old = """      zoning_evidence = (
          resolve_zoning_evidence(
              municipality=municipality,
              parcel=parcel,
          )
      )"""

    new = """      zoning_evidence = (
          resolve_zoning_evidence(
              municipality=municipality,
              parcel=parcel,
              zoning_resolution=zoning_resolution,
          )
      )"""

    if "zoning_resolution=zoning_resolution" in original:
        compile_file(MAIN)
        print("No API change required; zoning_resolution is already passed.")
        print("SUCCESS")
        print("==============================================")
        return

    if old not in original:
        raise RuntimeError(
            "Expected Stage C zoning_evidence call was not found exactly. "
            "No changes were made."
        )

    updated = original.replace(old, new, 1)

    # Validate before modifying the real file.
    temp = MAIN.with_name("main.py.stage-c-bridge-api-check")
    try:
        temp.write_text(updated, encoding="utf-8")
        compile_file(temp)
    finally:
        if temp.exists():
            temp.unlink()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-c-resolution-bridge-api-fix-{stamp}"
    )
    shutil.copy2(MAIN, backup)

    try:
        MAIN.write_text(updated, encoding="utf-8")
        compile_file(MAIN)
    except Exception:
        shutil.copy2(backup, MAIN)
        raise

    print("Backup:", backup)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Stage C now receives the existing zoning_resolution.")
    print("Block/Lot and authoritative-source checks remain in zoning_evidence.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
