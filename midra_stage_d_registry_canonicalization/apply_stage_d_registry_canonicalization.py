from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "app" / "services" / "zoning_evidence_registry.py"
RESOLVER = ROOT / "app" / "services" / "zoning_evidence.py"


def compile_file(path: Path) -> None:
    result = subprocess.run(
        ["python", "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"Syntax check failed for {path}.\n"
            f"{result.stdout}{result.stderr}"
        )


def backup(path: Path, label: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(f"{path.name}.before-{label}-{stamp}")
    shutil.copy2(path, target)
    return target


def main() -> None:
    print("==============================================")
    print("MIDRA Stage D — canonical registry cleanup")
    print("==============================================")
    print()

    if not REGISTRY.exists() or not RESOLVER.exists():
        raise RuntimeError("Required zoning evidence files were not found.")

    registry = REGISTRY.read_text(encoding="utf-8")
    resolver = RESOLVER.read_text(encoding="utf-8")

    old_alias_block = """    ("howell township", "177", "16.01"): {
        "zoning_district": "HD-4",
        "source": {
            "source_type": "municipal_zoning_evidence",
            "description": (
                "Verified Stage C parcel-specific zoning evidence "
                "registered for the Howell Township regression property."
            ),
            "authoritative": True,
        },
    },
    ("marlboro township", "177", "16"): {
        "zoning_district": "CF",
        "source": {
            "source_type": "municipal_zoning_evidence",
            "description": (
                "Verified Stage C parcel-specific zoning evidence "
                "registered for the Marlboro Township regression property."
            ),
            "authoritative": True,
        },
    },
"""

    if old_alias_block not in registry:
        raise RuntimeError(
            "Expected duplicate Township alias records were not found. "
            "No changes were made."
        )

    registry_new = registry.replace(old_alias_block, "", 1)

    old_import = (
        "from app.services.zoning_evidence_registry import "
        "VERIFIED_ZONING_EVIDENCE"
    )
    new_import = (
        "from app.services.zoning_evidence_registry "
        "import get_verified_zoning_evidence"
    )

    if old_import not in resolver:
        raise RuntimeError(
            "Expected direct registry import was not found. "
            "No changes were made."
        )

    resolver_new = resolver.replace(old_import, new_import, 1)

    old_lookup = """    legacy = VERIFIED_ZONING_EVIDENCE
    municipality_key = _normalize(municipality_value)
    legacy_record = legacy.get(
        (municipality_key, _normalize(block), _normalize(lot))
    )

    if legacy_record:
        district = _text(
            legacy_record.get("zoning_district")
            if isinstance(legacy_record, dict)
            else legacy_record
        )
        legacy_source = (
            legacy_record.get("source")
            if isinstance(legacy_record, dict)
            else None
        ) or {}

        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": district or "VERIFY",
"""

    new_lookup = """    municipality_key = _normalize(municipality_value)
    registry_record = get_verified_zoning_evidence(
        municipality_key=municipality_key,
        block=_normalize(block),
        lot=_normalize(lot),
    )

    if registry_record:
        district = _text(registry_record.get("zoning_district"))
        registry_source = registry_record.get("source") or {}

        return {
            "municipality": municipality_value,
            "block": block or None,
            "lot": lot or None,
            "status": "ZONING_RESOLVED",
            "zoning_district": district or "VERIFY",
"""

    if old_lookup not in resolver_new:
        raise RuntimeError(
            "Expected embedded registry lookup was not found. "
            "No changes were made."
        )

    resolver_new = resolver_new.replace(old_lookup, new_lookup, 1)

    old_source = """                "source_type": legacy_source.get(
                    "source_type",
                    "municipal_zoning_evidence",
                ),
                "description": legacy_source.get(
                    "description",
                    "Verified Stage C parcel-specific zoning evidence "
                    "registered for this test property.",
                ),
                "authoritative": bool(
                    legacy_source.get("authoritative", True)
                ),
"""

    new_source = """                "source_type": registry_source.get(
                    "source_type",
                    "municipal_zoning_evidence",
                ),
                "description": registry_source.get(
                    "description",
                    "Verified Stage D parcel-specific zoning evidence "
                    "registered for this property.",
                ),
                "authoritative": bool(
                    registry_source.get("authoritative", True)
                ),
"""

    if old_source not in resolver_new:
        raise RuntimeError(
            "Expected registry source metadata block was not found. "
            "No changes were made."
        )

    resolver_new = resolver_new.replace(old_source, new_source, 1)

    resolver_new = resolver_new.replace(
        "The legacy standalone Stage C test registry remains available for the\n"
        "two original verified test parcels.",
        "The Stage D registry contains explicitly verified parcel-specific evidence."
    )

    reg_tmp = REGISTRY.with_name("zoning_evidence_registry.py.stage-d-check")
    res_tmp = RESOLVER.with_name("zoning_evidence.py.stage-d-check")
    reg_tmp.write_text(registry_new, encoding="utf-8")
    res_tmp.write_text(resolver_new, encoding="utf-8")
    try:
        compile_file(reg_tmp)
        compile_file(res_tmp)
    finally:
        reg_tmp.unlink(missing_ok=True)
        res_tmp.unlink(missing_ok=True)

    reg_backup = backup(REGISTRY, "canonical-registry-cleanup")
    res_backup = backup(RESOLVER, "canonical-registry-cleanup")

    try:
        REGISTRY.write_text(registry_new, encoding="utf-8")
        RESOLVER.write_text(resolver_new, encoding="utf-8")
        compile_file(REGISTRY)
        compile_file(RESOLVER)
    except Exception:
        shutil.copy2(reg_backup, REGISTRY)
        shutil.copy2(res_backup, RESOLVER)
        raise

    print("Backups:")
    print(" ", reg_backup)
    print(" ", res_backup)
    print("Updated:")
    print(" ", REGISTRY)
    print(" ", RESOLVER)
    print()
    print("SUCCESS")
    print("Registry now has one canonical record per verified parcel.")
    print("TWP/Township aliases remain handled by resolver normalization.")
    print("Resolver now consumes the registry through its public getter.")
    print("Authoritative zoning-resolution bridge remains unchanged.")
    print("Municipality + Block/Lot matching remains mandatory.")
    print("Unknown combinations remain VERIFY.")
    print("All changed Python files passed syntax checks.")
    print("==============================================")


if __name__ == "__main__":
    main()
