
from pathlib import Path
import shutil
from datetime import datetime
import subprocess

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app" / "services" / "zoning_intelligence.py"

SOURCE_URL = (
    "https://www.twp.howell.nj.us/DocumentCenter/View/9871/"
    "O-23-42----HD-1S-Bulk-Standards-Table"
)

PATCH = r"""

# ============================================================
# MIDRA FINAL HOWELL HD-4 BULK OUTPUT OVERRIDE
#
# This is intentionally applied at the public service boundary.
# It guarantees that a resolved Howell HD-4 parcel receives
# the authoritative HD-4 numeric bulk schedule regardless of
# which upstream municipal-source branch produced its generic
# bulk list.
# ============================================================

_HOWELL_HD4_FINAL_BULK_SOURCE_URL = (
    "https://www.twp.howell.nj.us/DocumentCenter/View/9871/"
    "O-23-42----HD-1S-Bulk-Standards-Table"
)


def _howell_hd4_final_bulk_requirements() -> list[dict[str, Any]]:
    return [
        {
            "requirement": "Minimum lot area",
            "value": "40,000 sq ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 40,000 square feet minimum lot area for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm current parcel dimensions and any later "
                "amendments, variances, or site-specific approvals."
            ),
        },
        {
            "requirement": "Minimum lot frontage",
            "value": "150 ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 150 feet minimum lot frontage for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm frontage from the current survey and "
                "applicable frontage measurement rules."
            ),
        },
        {
            "requirement": "Minimum front yard setback",
            "value": "60 ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 60 feet minimum front yard setback for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm the applicable street line and current "
                "front-yard measurement under the ordinance."
            ),
        },
        {
            "requirement": "Minimum side yard",
            "value": "25 ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 25 feet minimum side yard for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm whether any corner-lot, easement, buffer, "
                "or site-specific provision changes the requirement."
            ),
        },
        {
            "requirement": "Minimum rear yard",
            "value": "25 ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 25 feet minimum rear yard for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm the applicable rear-yard measurement and "
                "any site-specific approval."
            ),
        },
        {
            "requirement": "Maximum impervious coverage",
            "value": "70%",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 70% maximum impervious coverage for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Calculate existing and proposed impervious coverage "
                "from the current survey/site plan."
            ),
        },
        {
            "requirement": "Maximum building height",
            "value": "45 ft",
            "applies_to": "HD-4",
            "basis": (
                "Howell Township Ordinance O-23-42 "
                "lists 45 feet maximum height for HD-4."
            ),
            "source": (
                "Howell Township Ordinance O-23-42 - "
                "HD-1S Bulk Standards Table"
            ),
            "source_section": "Bulk Standards Table / HD-4",
            "source_url": _HOWELL_HD4_FINAL_BULK_SOURCE_URL,
            "authoritative": True,
            "verification": (
                "Confirm the applicable height measurement method "
                "and any use-specific exception."
            ),
        },
    ]


_original_get_zoning_intelligence_before_final_hd4 = get_zoning_intelligence


def get_zoning_intelligence(
    municipality: str,
    project_goal: str | None = None,
    *args,
    **kwargs,
) -> dict[str, Any]:
    result = _original_get_zoning_intelligence_before_final_hd4(
        municipality,
        project_goal,
        *args,
        **kwargs,
    )

    if not isinstance(result, dict):
        return result

    municipality_value = str(
        result.get("municipality")
        or municipality
        or ""
    ).strip().lower()

    district_value = str(
        result.get("zoning_district")
        or ""
    ).strip().upper()

    if (
        municipality_value in {
            "howell township",
            "howell twp",
            "howell",
        }
        and district_value == "HD-4"
    ):
        result["bulk_requirements"] = (
            _howell_hd4_final_bulk_requirements()
        )

        verification_items = list(
            result.get("verification_items") or []
        )

        verification_items = [
            item
            for item in verification_items
            if "bulk" not in str(item).lower()
            or "not yet been loaded" not in str(item).lower()
        ]

        verification_items.append(
            "Current Howell Township HD-4 bulk standards are loaded "
            "from Ordinance O-23-42."
        )

        result["verification_items"] = list(
            dict.fromkeys(
                str(item)
                for item in verification_items
                if str(item).strip()
            )
        )

        result["confidence"] = (
            "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AND_BULK_AVAILABLE"
        )

        result["bulk_source"] = (
            _HOWELL_HD4_FINAL_BULK_SOURCE_URL
        )

    return result

"""

def compile_target():
    result = subprocess.run(
        ["python", "-m", "py_compile", str(TARGET)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"Syntax check failed:\n{result.stdout}\n{result.stderr}"
        )

def main():
    if not TARGET.exists():
        raise FileNotFoundError(TARGET)

    text = TARGET.read_text(encoding="utf-8")

    marker = "_original_get_zoning_intelligence_before_final_hd4"

    print("==============================================")
    print("MIDRA FINAL Howell HD-4 output connection")
    print("==============================================")
    print()

    if marker in text:
        print("Final HD-4 output override is already installed.")
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = TARGET.with_name(
            f"zoning_intelligence.py.before-final-hd4-output-{stamp}"
        )
        shutil.copy2(TARGET, backup)

        TARGET.write_text(
            text.rstrip() + "\n" + PATCH,
            encoding="utf-8",
        )

        print("Backup:", backup)
        print("Updated zoning_intelligence.py")

    print()
    print("Running syntax check...")
    compile_target()

    print()
    print("==============================================")
    print("SUCCESS")
    print("Howell HD-4 bulk output override is installed.")
    print("==============================================")

if __name__ == "__main__":
    main()
