from pathlib import Path
import shutil
import re
import subprocess
from datetime import datetime

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "app" / "main.py"

SOURCE_URL = 'https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table'
HD4_BLOCK = '            # ========================================================\n            # HOWELL HD-4 PROPERTY-SPECIFIC BULK STANDARDS\n            # ========================================================\n            # Applied only after property-specific zoning confirms HD-4.\n            if (\n                str(merged.get("municipality") or "").strip().lower()\n                in {"howell township", "howell twp", "howell"}\n                and resolved_district == "HD-4"\n            ):\n                merged["bulk_requirements"] = [\n                    {\n                        "requirement": "Minimum lot area",\n                        "value": "40,000 sq ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm current parcel dimensions and any later amendments, variances, or site-specific approvals.",\n                    },\n                    {\n                        "requirement": "Minimum lot frontage",\n                        "value": "150 ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm frontage from the current survey and applicable frontage measurement rules.",\n                    },\n                    {\n                        "requirement": "Minimum front yard setback",\n                        "value": "60 ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm the applicable street line and current front-yard measurement.",\n                    },\n                    {\n                        "requirement": "Minimum side yard",\n                        "value": "25 ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm any corner-lot, easement, buffer, or site-specific provision.",\n                    },\n                    {\n                        "requirement": "Minimum rear yard",\n                        "value": "25 ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm the applicable rear-yard measurement and any site-specific approval.",\n                    },\n                    {\n                        "requirement": "Maximum impervious coverage",\n                        "value": "70%",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Calculate existing and proposed impervious coverage from the current survey/site plan.",\n                    },\n                    {\n                        "requirement": "Maximum building height",\n                        "value": "45 ft",\n                        "applies_to": "HD-4",\n                        "source": "Howell Township Ordinance O-23-42 - HD-1S Bulk Standards Table",\n                        "source_section": "Bulk Standards Table / HD-4",\n                        "source_url": "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table",\n                        "authoritative": True,\n                        "verification": "Confirm the applicable height measurement method and any use-specific exception.",\n                    },\n                ]\n\n                merged["bulk_source"] = "https://www.twp.howell.nj.us/DocumentCenter/View/9871/O-23-42----HD-1S-Bulk-Standards-Table"\n                merged["confidence"] = (\n                    "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AND_BULK_AVAILABLE"\n                )\n'

def main():
    if not MAIN.exists():
        raise FileNotFoundError(MAIN)

    text = MAIN.read_text(encoding="utf-8")

    if "HOWELL HD-4 PROPERTY-SPECIFIC BULK STANDARDS" in text:
        print("Howell HD-4 bulk merge is already installed.")
        return

    branch_pattern = r"""(?m)^[ \t]*if[ \t]+resolved_district[ \t]*!=[ \t]*["']R-20["'][ \t]*:[ \t]*$"""
    branch_match = re.search(branch_pattern, text)

    if not branch_match:
        raise RuntimeError(
            'Could not locate `if resolved_district != "R-20":` in app/main.py. '
            "No file was changed."
        )

    branch_start = branch_match.end()

    bulk_pattern = r"""(?m)^[ \t]*merged[ \t]*\[[ \t]*["']bulk_requirements["'][ \t]*\][ \t]*=[ \t]*\[[ \t]*\][ \t]*$"""
    bulk_match = re.search(bulk_pattern, text[branch_start:])

    if not bulk_match:
        raise RuntimeError(
            'The NON-R-20 branch exists, but no '
            '`merged["bulk_requirements"] = []` assignment was found after it. '
            "No file was changed."
        )

    absolute_start = branch_start + bulk_match.start()
    absolute_end = branch_start + bulk_match.end()

    verified_pattern = r"""(?m)^[ \t]*#.*VERIFIED R-20 PARCEL"""
    verified_marker = re.search(verified_pattern, text[branch_start:])

    if verified_marker and absolute_start >= branch_start + verified_marker.start():
        raise RuntimeError(
            "The bulk reset was found outside the expected NON-R-20 branch. "
            "No file was changed."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN.with_name(
        f"main.py.before-howell-hd4-bulk-final-{stamp}"
    )
    shutil.copy2(MAIN, backup)

    new_text = (
        text[:absolute_end]
        + "\n\n"
        + HD4_BLOCK
        + "\n"
        + text[absolute_end:]
    )

    try:
        MAIN.write_text(new_text, encoding="utf-8")

        result = subprocess.run(
            ["python", "-m", "py_compile", str(MAIN)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            shutil.copy2(backup, MAIN)
            raise RuntimeError(
                "main.py failed syntax validation. The original file was restored.\n\n"
                + result.stdout
                + result.stderr
            )

    except Exception:
        shutil.copy2(backup, MAIN)
        raise

    print()
    print("==============================================")
    print("MIDRA Howell HD-4 bulk merge FINAL repair")
    print("==============================================")
    print()
    print("Backup:", backup)
    print("Updated:", MAIN)
    print()
    print("SUCCESS")
    print("Howell HD-4 numeric bulk standards are now connected.")
    print()
    print("Python syntax check passed.")
    print()
    print("Restart Uvicorn before testing the API.")

if __name__ == "__main__":
    main()
