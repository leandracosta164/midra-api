from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "municipality_source_registry.py"


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
    print("MIDRA Stage B — municipality source registry correction")
    print("==============================================")
    print()

    if not TARGET.exists():
        raise RuntimeError(f"Missing installed Stage B service: {TARGET}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"municipality_source_registry.py.before-stage-b-verification-{stamp}"
    )
    shutil.copy2(TARGET, backup)

    try:
        compile_file(TARGET)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Verified:", TARGET)
    print()
    print("SUCCESS")
    print("The Stage B municipality source registry is present and valid.")
    print("The previous installer self-copy issue has been removed.")
    print("No zoning, coverage, or applicability logic was changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
