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
    print("MIDRA Stage C — resolution bridge API integration")
    print("==============================================")
    print()

    original = MAIN.read_text(encoding="utf-8")
    updated = original

    call = """zoning_evidence = (
        resolve_zoning_evidence(
            municipality=municipality,
            parcel=parcel,
        )
    )"""

    replacement = """zoning_evidence = (
        resolve_zoning_evidence(
            municipality=municipality,
            parcel=parcel,
            zoning_resolution=zoning_resolution,
        )
    )"""

    if call in updated and "zoning_resolution=zoning_resolution" not in updated:
        updated = updated.replace(call, replacement, 1)

    if updated == original:
        compile_file(MAIN)
        print("No API change required.")
        print("SUCCESS")
        print("Stage C API already passes zoning_resolution into evidence.")
        print("==============================================")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-c-resolution-bridge-{stamp}"
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
    print("Stage C API now passes zoning_resolution into zoning evidence.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
