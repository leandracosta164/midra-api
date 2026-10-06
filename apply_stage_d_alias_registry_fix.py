from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "app" / "services" / "zoning_evidence_registry.py"


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
    print("MIDRA Stage D — registry municipality alias fix")
    print("==============================================")
    print()

    if not REGISTRY.exists():
        raise RuntimeError(f"Missing target: {REGISTRY}")

    current = REGISTRY.read_text(encoding="utf-8")

    required = [
        '("howell township", "177", "16.01")',
        '("marlboro township", "177", "16")',
    ]
    for marker in required:
        if marker not in current:
            raise RuntimeError(
                f"Expected registry record {marker} was not found. "
                "No changes were made."
            )

    if (
        '("howell twp", "177", "16.01")' in current
        and '("marlboro twp", "177", "16")' in current
    ):
        compile_file(REGISTRY)
        print("TWP aliases are already present.")
        print("No changes made.")
        print("SUCCESS")
        return

    additions = (
        '    ("howell twp", "177", "16.01"): {\n'
        '        "zoning_district": "HD-4",\n'
        '        "source": {\n'
        '            "source_type": "municipal_zoning_evidence",\n'
        '            "description": "Verified Stage C parcel-specific zoning evidence registered for the Howell Township regression property.",\n'
        '            "authoritative": True,\n'
        '        },\n'
        '    },\n'
        '    ("marlboro twp", "177", "16"): {\n'
        '        "zoning_district": "CF",\n'
        '        "source": {\n'
        '            "source_type": "municipal_zoning_evidence",\n'
        '            "description": "Verified Stage C parcel-specific zoning evidence registered for the Marlboro Township regression property.",\n'
        '            "authoritative": True,\n'
        '        },\n'
        '    },\n'
    )

    anchor = 'VERIFIED_ZONING_EVIDENCE: dict[tuple[str, str, str], dict[str, Any]] = {\n'
    if anchor not in current:
        raise RuntimeError("Expected registry dictionary anchor was not found.")

    updated = current.replace(anchor, anchor + additions, 1)

    temp = REGISTRY.with_name("zoning_evidence_registry.py.stage-d-alias-check")
    temp.write_text(updated, encoding="utf-8")
    try:
        compile_file(temp)
    finally:
        temp.unlink(missing_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = REGISTRY.with_name(
        f"zoning_evidence_registry.py.before-twp-alias-fix-{stamp}"
    )
    shutil.copy2(REGISTRY, backup)

    try:
        REGISTRY.write_text(updated, encoding="utf-8")
        compile_file(REGISTRY)
    except Exception:
        shutil.copy2(backup, REGISTRY)
        raise

    print("Backup:", backup)
    print("Updated:", REGISTRY)
    print()
    print("SUCCESS")
    print("Stage D registry now supports Township/TWP aliases.")
    print("Existing evidence values are unchanged.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("Unknown combinations remain VERIFY.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
