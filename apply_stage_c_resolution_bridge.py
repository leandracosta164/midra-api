from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = (
    ROOT / "midra_stage_c_resolution_bridge"
    / "app"
    / "services"
    / "zoning_evidence.py"
)
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
    print("MIDRA Stage C — zoning resolution evidence bridge")
    print("==============================================")
    print()

    if not SOURCE.exists():
        raise RuntimeError(f"Missing source file: {SOURCE}")
    if not TARGET.exists():
        raise RuntimeError(f"Missing installed Stage C file: {TARGET}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"zoning_evidence.py.before-resolution-bridge-{stamp}"
    )

    shutil.copy2(TARGET, backup)

    try:
        shutil.copy2(SOURCE, TARGET)
        compile_file(TARGET)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Updated:", TARGET)
    print()
    print("SUCCESS")
    print("Stage C now accepts verified parcel-specific zoning resolution evidence.")
    print("Block/Lot matching and authoritative-source checks are required.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
