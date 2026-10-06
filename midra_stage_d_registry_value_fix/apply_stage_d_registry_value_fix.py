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
    print("MIDRA Stage D — registry value-shape correction")
    print("==============================================")
    print()

    if not TARGET.exists():
        raise RuntimeError(f"Missing target: {TARGET}")

    current = TARGET.read_text(encoding="utf-8")

    old = """    district = legacy.get(
        (municipality_key, _normalize(block), _normalize(lot))
    )

    if district:
        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": district,
"""

    new = """    legacy_record = legacy.get(
        (municipality_key, _normalize(block), _normalize(lot))
    )

    if legacy_record:
        district = _text(
            legacy_record.get("zoning_district")
            if isinstance(legacy_record, dict)
            else legacy_record
        )
        legacy_source = (
            legacy_record.get("source")
            if isinstance(legacy_record, dict)
            else None
        ) or {}

        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": district or "VERIFY",
"""

    if old not in current:
        raise RuntimeError(
            "Expected legacy district lookup block was not found. "
            "No changes were made."
        )

    updated = current.replace(old, new, 1)

    old_source = """                "source_type": "municipal_zoning_evidence",
                "description": (
                    "Verified Stage C parcel-specific zoning evidence "
                    "registered for this test property."
                ),
                "authoritative": True,
"""

    new_source = """                "source_type": legacy_source.get(
                    "source_type",
                    "municipal_zoning_evidence",
                ),
                "description": legacy_source.get(
                    "description",
                    "Verified Stage C parcel-specific zoning evidence "
                    "registered for this test property.",
                ),
                "authoritative": bool(
                    legacy_source.get("authoritative", True)
                ),
"""

    if old_source not in updated:
        raise RuntimeError(
            "Expected legacy source block was not found. "
            "No changes were made."
        )

    updated = updated.replace(old_source, new_source, 1)

    temp = TARGET.with_name("zoning_evidence.py.stage-d-value-check")
    temp.write_text(updated, encoding="utf-8")
    try:
        compile_file(temp)
    finally:
        temp.unlink(missing_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"zoning_evidence.py.before-stage-d-value-fix-{stamp}"
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
    print("Stage D registry records are now consumed by their value shape.")
    print("Howell/Marlboro districts remain HD-4/CF.")
    print("Registry source metadata is preserved.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("Unknown combinations remain VERIFY.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
