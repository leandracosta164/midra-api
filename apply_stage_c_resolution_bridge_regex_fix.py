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


def main() -> None:
    print("==============================================")
    print("MIDRA Stage C — regex API resolution bridge fix")
    print("==============================================")
    print()

    original = MAIN.read_text(encoding="utf-8")

    # Target ONLY the Stage C call by anchoring it to the preceding
    # zoning_evidence assignment. Whitespace is intentionally flexible.
    pattern = (
        r'(?P<prefix>zoning_evidence\s*=\s*\(\s*'
        r'resolve_zoning_evidence\s*\(\s*'
        r'municipality\s*=\s*municipality\s*,\s*'
        r'parcel\s*=\s*parcel\s*,)'
        r'(?P<close>\s*\)\s*\))'
    )

    if "zoning_resolution=zoning_resolution" in re.search(
        r'zoning_evidence\s*=\s*\(\s*resolve_zoning_evidence\s*\(.*?\)',
        original,
        flags=re.DOTALL,
    ).group(0) if re.search(
        r'zoning_evidence\s*=\s*\(\s*resolve_zoning_evidence\s*\(.*?\)',
        original,
        flags=re.DOTALL,
    ) else "":
        compile_file(MAIN)
        print("No change required; Stage C call already passes zoning_resolution.")
        print("SUCCESS")
        print("==============================================")
        return

    match = re.search(pattern, original, flags=re.DOTALL)
    if not match:
        raise RuntimeError(
            "Could not locate the Stage C resolve_zoning_evidence call "
            "by structure. No changes were made."
        )

    replacement = (
        match.group("prefix")
        + "\n"
        + "              zoning_resolution=zoning_resolution,"
        + match.group("close")
    )

    updated = original[:match.start()] + replacement + original[match.end():]

    # Validate proposed file before modifying the real file.
    temp = MAIN.with_name("main.py.stage-c-regex-api-check")
    try:
        temp.write_text(updated, encoding="utf-8")
        compile_file(temp)
    finally:
        if temp.exists():
            temp.unlink()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-stage-c-regex-api-fix-{stamp}"
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
    print("Only the Stage C resolve_zoning_evidence call was changed.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
