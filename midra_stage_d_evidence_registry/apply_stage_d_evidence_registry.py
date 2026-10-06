from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
SERVICES = ROOT / "app" / "services"
EVIDENCE = SERVICES / "zoning_evidence.py"
REGISTRY = SERVICES / "zoning_evidence_registry.py"

REGISTRY_TEXT = '"""Stage D verified parcel-specific zoning evidence registry."""\nfrom __future__ import annotations\nfrom typing import Any\n\nVERIFIED_ZONING_EVIDENCE: dict[tuple[str, str, str], dict[str, Any]] = {\n    ("howell township", "177", "16.01"): {\n        "zoning_district": "HD-4",\n        "source": {\n            "source_type": "municipal_zoning_evidence",\n            "description": "Verified Stage C parcel-specific zoning evidence registered for the Howell Township regression property.",\n            "authoritative": True,\n        },\n    },\n    ("marlboro township", "177", "16"): {\n        "zoning_district": "CF",\n        "source": {\n            "source_type": "municipal_zoning_evidence",\n            "description": "Verified Stage C parcel-specific zoning evidence registered for the Marlboro Township regression property.",\n            "authoritative": True,\n        },\n    },\n}\n\ndef get_verified_zoning_evidence(*, municipality_key: str, block: str, lot: str) -> dict[str, Any] | None:\n    record = VERIFIED_ZONING_EVIDENCE.get((municipality_key, block, lot))\n    if not record:\n        return None\n    return {**record, "source": dict(record.get("source") or {})}\n'

def compile_file(path: Path) -> None:
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Syntax check failed for {path}.\\n{result.stdout}{result.stderr}"
        )

def main() -> None:
    print("==============================================")
    print("MIDRA Stage D — evidence registry architecture")
    print("==============================================")
    print()

    if not EVIDENCE.exists():
        raise RuntimeError(f"Missing target: {EVIDENCE}")

    current = EVIDENCE.read_text(encoding="utf-8")

    if "from app.services.zoning_evidence_registry import VERIFIED_ZONING_EVIDENCE" in current:
        compile_file(EVIDENCE)
        print("Stage D registry import already exists.")
        print("No changes made.")
        print("SUCCESS")
        return

    REGISTRY.write_text(REGISTRY_TEXT, encoding="utf-8")
    compile_file(REGISTRY)

    pattern = re.compile(
        r"^[ \t]*# Preserve the two original verified Stage C standalone test parcels\\.\\r?\\n"
        r"^[ \t]*legacy = \\{.*?^[ \t]*\\}\\r?\\n",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(current)
    if not match:
        REGISTRY.unlink(missing_ok=True)
        raise RuntimeError(
            "The current standalone Stage C legacy registry was not found. "
            "No zoning_evidence.py changes were made."
        )

    replacement = "    legacy = VERIFIED_ZONING_EVIDENCE\\n"
    updated = current[:match.start()] + replacement + current[match.end():]

    marker = "from __future__ import annotations\\n"
    import_line = (
        "from app.services.zoning_evidence_registry import "
        "VERIFIED_ZONING_EVIDENCE\\n"
    )
    if marker not in updated:
        REGISTRY.unlink(missing_ok=True)
        raise RuntimeError("Expected future-import marker was not found.")

    updated = updated.replace(marker, marker + "\\n" + import_line, 1)

    temp = EVIDENCE.with_name("zoning_evidence.py.stage-d-check")
    temp.write_text(updated, encoding="utf-8")
    try:
        compile_file(temp)
    finally:
        temp.unlink(missing_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = EVIDENCE.with_name(
        f"zoning_evidence.py.before-stage-d-registry-{stamp}"
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
    print("Unknown municipality/Block/Lot combinations remain VERIFY.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("The authoritative zoning-resolution bridge was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")

if __name__ == "__main__":
    main()
