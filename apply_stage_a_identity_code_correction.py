from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "municipality_identity.py"

OLD = """# Stage A identity mapping only. This does not imply zoning coverage.
KNOWN_NJ_MUNICIPALITY_CODES: dict[str, str] = {
    "howell township": "1321",
    "marlboro township": "1322",
}
"""

NEW = """# Stage A deliberately does not maintain a hand-coded municipality-code
# table. When an authoritative parcel resolver supplies a municipality code,
# that source value is preserved by resolve_municipality_identity().
"""


def compile_file(path: Path) -> None:
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Syntax check failed for {path}.\\n"
            f"{result.stdout}{result.stderr}"
        )


def main() -> None:
    print("==============================================")
    print("MIDRA Stage A — municipality code correction")
    print("==============================================")
    print()

    if not TARGET.exists():
        raise RuntimeError(f"Missing required file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    if OLD not in text:
        raise RuntimeError(
            "Expected hard-coded Stage A municipality-code table was not "
            "found. No changes were made."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(
        f"municipality_identity.py.before-code-correction-{stamp}"
    )
    shutil.copy2(TARGET, backup)

    try:
        text = text.replace(OLD, NEW, 1)
        text = text.replace(
            'or KNOWN_NJ_MUNICIPALITY_CODES.get(normalized)',
            'or None',
            1,
        )
        TARGET.write_text(text, encoding="utf-8")
        compile_file(TARGET)
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print("Backup:", backup)
    print("Updated:", TARGET)
    print()
    print("SUCCESS")
    print("Hard-coded municipality-code fallbacks were removed.")
    print("Authoritative parcel-supplied municipality codes remain preserved.")
    print("Municipality recognition logic was not changed.")
    print("No zoning, coverage, or applicability logic was changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
