from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"
TARGET = ROOT / "app" / "services" / "municipality_identity.py"

SERVICE_SOURCE = 'from __future__ import annotations\n\nfrom typing import Any\n\nfrom app.services.zoning_intelligence import MUNICIPALITY_SOURCES\n\n# Stage A identity mapping only. This does not imply zoning coverage.\nKNOWN_NJ_MUNICIPALITY_CODES: dict[str, str] = {\n    "howell township": "1321",\n    "marlboro township": "1322",\n}\n\n\ndef _normalize(value: object) -> str:\n    return " ".join(str(value or "").strip().lower().split())\n\n\ndef _canonical_from_registry(municipality: str | None) -> str | None:\n    key = _normalize(municipality)\n    if not key:\n        return None\n\n    aliases = {\n        "howell": "howell township",\n        "howell twp": "howell township",\n        "marlboro": "marlboro township",\n        "marlboro twp": "marlboro township",\n    }\n    registry_key = aliases.get(key, key)\n\n    config = MUNICIPALITY_SOURCES.get(registry_key)\n    if config:\n        return str(config.get("canonical_name") or registry_key)\n\n    for config in MUNICIPALITY_SOURCES.values():\n        if _normalize(config.get("canonical_name")) == key:\n            return str(config.get("canonical_name") or key)\n\n    return None\n\n\ndef resolve_municipality_identity(\n    municipality: str | None,\n    *,\n    county: str | None = None,\n    state: str | None = "New Jersey",\n    municipality_code: str | None = None,\n) -> dict[str, Any]:\n    """Resolve municipality identity without making zoning claims."""\n    supplied = str(municipality or "").strip()\n    canonical = _canonical_from_registry(supplied)\n\n    if not canonical:\n        return {\n            "status": "MUNICIPALITY_NOT_RECOGNIZED",\n            "recognized": False,\n            "municipality": supplied or None,\n            "canonical_name": None,\n            "county": county,\n            "state": state,\n            "municipality_code": municipality_code,\n            "identity_source": {\n                "source_type": "NJ Office of GIS",\n                "authoritative": True,\n                "mode": "stage_a_registry_identity",\n            },\n            "notes": [\n                "Municipality identity could not be matched to the "\n                "currently loaded MIDRA identity registry.",\n                "This does not establish that the municipality lacks "\n                "authoritative zoning information.",\n            ],\n        }\n\n    normalized = _normalize(canonical)\n    config = MUNICIPALITY_SOURCES.get(normalized) or {}\n\n    return {\n        "status": "MUNICIPALITY_RECOGNIZED",\n        "recognized": True,\n        "municipality": supplied or canonical,\n        "canonical_name": canonical,\n        "county": county or config.get("county"),\n        "state": state or config.get("state") or "New Jersey",\n        "municipality_code": (\n            municipality_code\n            or KNOWN_NJ_MUNICIPALITY_CODES.get(normalized)\n        ),\n        "identity_source": {\n            "source_type": "NJ Office of GIS",\n            "authoritative": True,\n            "mode": "stage_a_registry_identity",\n        },\n        "notes": [\n            "Stage A establishes municipality identity only.",\n            "Municipality recognition does not imply zoning-source "\n            "verification or project-rule availability.",\n        ],\n    }\n\n\nbuild_municipality_identity = resolve_municipality_identity\n'


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
    print("MIDRA Stage A — municipality identity")
    print("==============================================")
    print()

    if not MAIN.exists():
        raise RuntimeError(f"Missing required file: {MAIN}")

    TARGET.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = None
    if TARGET.exists():
        backup = TARGET.with_name(
            f"municipality_identity.py.before-stage-a-{stamp}"
        )
        shutil.copy2(TARGET, backup)

    try:
        TARGET.write_text(SERVICE_SOURCE, encoding="utf-8")
        compile_file(TARGET)
        compile_file(MAIN)
    except Exception:
        if backup and backup.exists():
            shutil.copy2(backup, TARGET)
        elif TARGET.exists():
            TARGET.unlink()
        raise

    print("Added/updated:", TARGET)
    if backup:
        print("Backup:", backup)
    print()
    print("SUCCESS")
    print("Stage A municipality identity service is installed.")
    print("Identity recognition is kept separate from zoning coverage.")
    print("No zoning rules or applicability logic were changed.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
