from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "zoning_evidence.py"


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
    print("MIDRA Stage C — municipality match correction")
    print("==============================================")
    print()

    original = TARGET.read_text(encoding="utf-8")

    old = """    if (
        resolution.get("status") == "ZONING_RESOLVED"
        and resolution.get("confidence") == "OFFICIAL_PARCEL_SPECIFIC"
        and bool((resolution.get("source") or {}).get("authoritative"))
        and _same_parcel(parcel_data, resolution)
    ):"""

    new = """    resolution_source = resolution.get("source") or {}
    resolution_municipality = (
        resolution.get("municipality")
        or resolution_source.get("municipality")
    )

    if (
        resolution.get("status") == "ZONING_RESOLVED"
        and resolution.get("confidence") == "OFFICIAL_PARCEL_SPECIFIC"
        and bool(resolution_source.get("authoritative"))
        and _normalize(municipality_value) == _normalize(resolution_municipality)
        and _same_parcel(parcel_data, resolution)
    ):"""

    if new in original:
        compile_file(TARGET)
        print("No change required; municipality matching is already enforced.")
        print("SUCCESS")
        print("==============================================")
        return

    if old not in original:
        raise RuntimeError(
            "Expected Stage C resolution acceptance block was not found. "
            "No changes were made."
        )

    updated = original.replace(old, new, 1)

    temp = TARGET.with_name("zoning_evidence.py.municipality-check")
    try:
        temp.write_text(updated, encoding="utf-8")
        compile_file(temp)
    finally:
        if temp.exists():
            temp.unlink()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"zoning_evidence.py.before-municipality-match-fix-{stamp}"
    )
    shutil.copy2(TARGET, backup)

    try:
        TARGET.write_text(updated, encoding="utf-8")
        compile_file(TARGET)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Updated:", TARGET)
    print()
    print("SUCCESS")
    print("Stage C now requires municipality + Block/Lot agreement.")
    print("A zoning result from another municipality cannot be inherited.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
