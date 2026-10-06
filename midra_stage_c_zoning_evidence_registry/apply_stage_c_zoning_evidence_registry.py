from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "zoning_evidence.py"
SOURCE = (
    ROOT / "midra_stage_c_zoning_evidence_registry"
    / "app" / "services" / "zoning_evidence.py"
)


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
    print("MIDRA Stage C — zoning evidence registry")
    print("==============================================")
    print()

    if not SOURCE.exists():
        raise RuntimeError(f"Missing source file: {SOURCE}")

    TARGET.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = None

    if TARGET.exists():
        backup = TARGET.with_name(
            f"zoning_evidence.py.before-stage-c-{stamp}"
        )
        shutil.copy2(TARGET, backup)

    try:
        shutil.copy2(SOURCE, TARGET)
        compile_file(TARGET)
    except Exception:
        if backup and backup.exists():
            shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup if backup else "None — new file")
    print("Added/updated:", TARGET)
    print()
    print("SUCCESS")
    print("Stage C zoning evidence registry is installed.")
    print("Only verified parcel-specific evidence is eligible to resolve zoning.")
    print("Unknown municipality/Block/Lot combinations remain VERIFY.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
