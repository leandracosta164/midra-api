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
    print("MIDRA Stage C — API integration")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing main.py: {MAIN}")

    original = MAIN.read_text(encoding="utf-8")

    import_marker = (
        "from app.services.municipality_source_registry import "
        "resolve_municipality_source\n"
    )
    import_line = (
        "from app.services.zoning_evidence import resolve_zoning_evidence\n"
    )

    if import_line not in original:
        if import_marker not in original:
            raise RuntimeError(
                "Expected Stage B import marker was not found in main.py. "
                "No changes were made."
            )
        updated = original.replace(
            import_marker,
            import_marker + import_line,
            1,
        )
    else:
        updated = original

    zoning_call_marker = (
        "      zoning_resolution = (\n"
        "          resolve_property_zoning(\n"
        "              municipality=municipality,\n"
        "              parcel=parcel,\n"
        "          )\n"
        "      )\n"
    )

    evidence_block = (
        "\n"
        "      # ========================================================\n"
        "      # STEP 2B — STAGE C ZONING EVIDENCE\n"
        "      # ========================================================\n"
        "      #\n"
        "      # Stage C exposes verified parcel-specific zoning evidence\n"
        "      # separately. It does not replace the existing zoning\n"
        "      # resolver or change downstream zoning/applicability logic.\n"
        "      # ========================================================\n"
        "\n"
        "      zoning_evidence = (\n"
        "          resolve_zoning_evidence(\n"
        "              municipality=municipality,\n"
        "              parcel=parcel,\n"
        "          )\n"
        "      )\n"
    )

    if "resolve_zoning_evidence(" not in updated:
        if zoning_call_marker not in updated:
            raise RuntimeError(
                "Expected zoning resolution block was not found in main.py. "
                "No changes were made."
            )
        updated = updated.replace(
            zoning_call_marker,
            zoning_call_marker + evidence_block,
            1,
        )

    response_anchor = (
        '          "municipality_source_registry": (\n'
        '              municipality_source_registry\n'
        "          ),\n"
    )

    response_block = (
        "\n"
        '          "zoning_evidence": (\n'
        "              zoning_evidence\n"
        "          ),\n"
    )

    if '"zoning_evidence":' not in updated:
        if response_anchor not in updated:
            raise RuntimeError(
                "Expected Stage B response anchor was not found in main.py. "
                "No changes were made."
            )
        updated = updated.replace(
            response_anchor,
            response_anchor + response_block,
            1,
        )

    if updated == original:
        print("No changes required; Stage C integration already present.")
        compile_file(MAIN)
        print("SUCCESS")
        print("Stage C API integration is already present.")
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
