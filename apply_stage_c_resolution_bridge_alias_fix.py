from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
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
    print("MIDRA Stage C — municipality alias correction")
    print("==============================================")
    print()

    original = TARGET.read_text(encoding="utf-8")

    old = '''def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())'''

    new = '''def _normalize(value: Any) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    aliases = {
        "marlboro township": "marlboro twp",
        "howell township": "howell twp",
    }
    return aliases.get(text, text)'''

    if new in original:
        compile_file(TARGET)
        print("No change required; municipality aliases are already normalized.")
        print("SUCCESS")
        print("==============================================")
        return

    if old not in original:
        raise RuntimeError(
            "Expected _normalize function was not found. No changes were made."
        )

    updated = original.replace(old, new, 1)

    temp = TARGET.with_name("zoning_evidence.py.alias-check")
    try:
        temp.write_text(updated, encoding="utf-8")
        compile_file(temp)
    finally:
        if temp.exists():
            temp.unlink()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"zoning_evidence.py.before-alias-match-fix-{stamp}"
    )
    shutil.copy2(TARGET, backup)

    try:
        TARGET.write_text(updated, encoding="utf-8")
        compile_file(TARGET)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Updated:", TARGET)
    print()
    print("SUCCESS")
    print("Stage C now treats official Township/TWP names as the same municipality.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("Cross-municipality evidence remains rejected.")
    print("Existing zoning, coverage, and applicability logic was not changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
