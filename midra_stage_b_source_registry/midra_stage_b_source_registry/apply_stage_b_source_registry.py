from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "municipality_source_registry.py"
SOURCE = ROOT / "midra_stage_b_source_registry" / "app" / "services" / "municipality_source_registry.py"


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
    print("MIDRA Stage B — municipality source registry")
    print("==============================================")
    print()

    if not SOURCE.exists():
        raise RuntimeError(f"Missing source file: {SOURCE}")

    TARGET.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = None

    if TARGET.exists():
        backup = TARGET.with_name(
            f"municipality_source_registry.py.before-stage-b-{stamp}"
        )
        shutil.copy2(TARGET, backup)
        print("Backup:", backup)

    try:
        shutil.copy2(SOURCE, TARGET)
        compile_file(TARGET)
    except Exception:
        if backup and backup.exists():
            shutil.copy2(backup, TARGET)
        raise

    print("Added/updated:", TARGET)
    print()
    print("SUCCESS")
    print("Stage B municipality source registry is installed.")
    print("The registry identifies official municipal zoning sources only.")
    print("No zoning resolution, coverage, or applicability logic was changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
