from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "app" / "services" / "zoning_evidence.py"
REGISTRY = ROOT / "app" / "services" / "zoning_evidence_registry.py"

REGISTRY_TEXT = '"""Stage D — verified parcel-specific zoning evidence registry.\n\nEvidence records live here so the registry can grow without changing\nthe resolver logic. Only explicitly verified parcel-specific evidence\nbelongs in this module.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any\n\n\nVERIFIED_ZONING_EVIDENCE: dict[tuple[str, str, str], dict[str, Any]] = {\n    ("howell township", "177", "16.01"): {\n        "zoning_district": "HD-4",\n        "source": {\n            "source_type": "municipal_zoning_evidence",\n            "description": (\n                "Verified Stage C parcel-specific zoning evidence "\n                "registered for the Howell Township regression property."\n            ),\n            "authoritative": True,\n        },\n    },\n    ("marlboro township", "177", "16"): {\n        "zoning_district": "CF",\n        "source": {\n            "source_type": "municipal_zoning_evidence",\n            "description": (\n                "Verified Stage C parcel-specific zoning evidence "\n                "registered for the Marlboro Township regression property."\n            ),\n            "authoritative": True,\n        },\n    },\n}\n\n\ndef get_verified_zoning_evidence(\n    *,\n    municipality_key: str,\n    block: str,\n    lot: str,\n) -> dict[str, Any] | None:\n    """Return a defensive copy of a verified evidence record."""\n    record = VERIFIED_ZONING_EVIDENCE.get(\n        (municipality_key, block, lot)\n    )\n    if not record:\n        return None\n\n    return {\n        **record,\n        "source": dict(record.get("source") or {}),\n    }\n'


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
    print("MIDRA Stage D — evidence registry architecture v2")
    print("==============================================")
    print()

    if not EVIDENCE.exists():
        raise RuntimeError(f"Missing target: {EVIDENCE}")

    current = EVIDENCE.read_text(encoding="utf-8")

    if (
        "from app.services.zoning_evidence_registry "
        "import VERIFIED_ZONING_EVIDENCE"
    ) in current:
        compile_file(EVIDENCE)
        print("Stage D registry import already exists.")
        print("No changes made.")
        print("SUCCESS")
        print("==============================================")
        return

    # Locate the exact legacy registry by stable source markers.
    start_marker = (
        "    # Preserve the two original verified Stage C standalone "
        "test parcels.\n"
    )
    end_marker = (
        "    municipality_key = _normalize(municipality_value)\n"
    )

    start = current.find(start_marker)
    if start < 0:
        raise RuntimeError(
            "The current Stage C legacy-registry start marker was not found. "
            "No changes were made."
        )

    end = current.find(end_marker, start)
    if end < 0:
        raise RuntimeError(
            "The current Stage C legacy-registry end marker was not found. "
            "No changes were made."
        )

    legacy_block = current[start:end]

    if "legacy = {" not in legacy_block:
        raise RuntimeError(
            "The located Stage C block did not contain the expected legacy "
            "dictionary. No changes were made."
        )

    replacement = "    legacy = VERIFIED_ZONING_EVIDENCE\n"
    updated = current[:start] + replacement + current[end:]

    import_line = (
        "from app.services.zoning_evidence_registry "
        "import VERIFIED_ZONING_EVIDENCE\n"
    )
    future_marker = "from __future__ import annotations\n"

    if import_line not in updated:
        if future_marker not in updated:
            raise RuntimeError(
                "Expected future-import marker was not found. "
                "No changes were made."
            )
        updated = updated.replace(
            future_marker,
            future_marker + "\n" + import_line,
            1,
        )

    # Write the registry and validate both files before changing the target.
    REGISTRY.write_text(REGISTRY_TEXT, encoding="utf-8")
    compile_file(REGISTRY)

    temp = EVIDENCE.with_name("zoning_evidence.py.stage-d-check")
    temp.write_text(updated, encoding="utf-8")
    try:
        compile_file(temp)
    finally:
        temp.unlink(missing_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = EVIDENCE.with_name(
        f"zoning_evidence.py.before-stage-d-registry-v2-{stamp}"
    )
    shutil.copy2(EVIDENCE, backup)

    try:
        EVIDENCE.write_text(updated, encoding="utf-8")
        compile_file(EVIDENCE)
    except Exception:
        shutil.copy2(backup, EVIDENCE)
        raise

    print("Backup:", backup)
    print("Added:", REGISTRY)
    print("Updated:", EVIDENCE)
    print()
    print("SUCCESS")
    print("Stage D registry architecture is installed.")
    print("Existing Howell and Marlboro regression evidence is preserved.")
    print("Resolver validation logic remains unchanged.")
    print("Unknown municipality/Block/Lot combinations remain VERIFY.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("The authoritative zoning-resolution bridge was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
