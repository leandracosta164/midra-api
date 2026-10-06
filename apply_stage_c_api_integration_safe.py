from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
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


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(
            f"Could not locate the expected {label} in main.py. "
            "No changes were made."
        )
    return updated


def main() -> None:
    print("==============================================")
    print("MIDRA Stage C — safe API integration")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing main.py: {MAIN}")

    original = MAIN.read_text(encoding="utf-8")
    updated = original

    import_line = "from app.services.zoning_evidence import resolve_zoning_evidence"

    if import_line not in updated:
        import_pattern = (
            r"^(from app\.services\.municipality_source_registry import "
            r"resolve_municipality_source\s*)$"
        )
        updated = replace_once(
            updated,
            import_pattern,
            r"\1\n" + import_line,
            "Stage B import",
        )

    if "zoning_evidence = (" not in updated:
        # Match the complete existing zoning_resolution assignment while
        # preserving whatever indentation the current main.py uses.
        zoning_pattern = (
            r"(?m)^([ \t]*)zoning_resolution = \(\n"
            r"\1    resolve_property_zoning\(\n"
            r"\1        municipality=municipality,\n"
            r"\1        parcel=parcel,\n"
            r"\1    \)\n"
            r"\1\)"
        )

        evidence_template = (
            r"\g<0>\n\n"
            r"\1# ========================================================\n"
            r"\1# STEP 2B — STAGE C ZONING EVIDENCE\n"
            r"\1# ========================================================\n"
            r"\1#\n"
            r"\1# Stage C exposes verified parcel-specific zoning evidence\n"
            r"\1# separately. It does not replace the existing zoning resolver\n"
            r"\1# or change downstream zoning/applicability logic.\n"
            r"\1# ========================================================\n\n"
            r"\1zoning_evidence = (\n"
            r"\1    resolve_zoning_evidence(\n"
            r"\1        municipality=municipality,\n"
            r"\1        parcel=parcel,\n"
            r"\1    )\n"
            r"\1)"
        )

        updated = replace_once(
            updated,
            zoning_pattern,
            evidence_template,
            "property-specific zoning block",
        )

    if '"zoning_evidence":' not in updated:
        response_pattern = (
            r'(?m)^([ \t]*)"municipality_source_registry": \(\n'
            r'\1    municipality_source_registry\n'
            r'\1\),'
        )

        response_template = (
            r'\g<0>\n'
            r'\1"zoning_evidence": (\n'
            r'\1    zoning_evidence\n'
            r'\1),'
        )

        updated = replace_once(
            updated,
            response_pattern,
            response_template,
            "Stage B response field",
        )

    # Always validate the proposed result before touching the real file.
    temp = MAIN.with_name("main.py.stage-c-integration-check")
    try:
        temp.write_text(updated, encoding="utf-8")
        compile_file(temp)
    finally:
        if temp.exists():
            temp.unlink()

    if updated == original:
        print("No changes required; Stage C integration is already present.")
        print("SUCCESS")
        print("Existing zoning, coverage, and applicability logic was preserved.")
        print("All changed Python files passed syntax checks.")
        print("==============================================")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-c-integration-{stamp}"
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
    print("Stage C zoning evidence is integrated into main.py.")
    print("The existing zoning resolver remains intact.")
    print("Stage C is exposed separately as zoning_evidence.")
    print("Existing coverage and applicability logic was not replaced.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
