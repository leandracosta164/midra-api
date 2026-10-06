from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SERVICES = ROOT / "app" / "services"

ZONING = SERVICES / "zoning_intelligence.py"
MAIN = ROOT / "app" / "main.py"


def backup(path: Path) -> None:
    target = path.with_suffix(
        path.suffix + ".before-howell-rules"
    )
    shutil.copy2(path, target)
    print(f"Backup: {target}")


def add_howell_rule_function() -> None:
    text = ZONING.read_text(
        encoding="utf-8"
    )

    if "def _build_howell_pool_requirements(" in text:
        print(
            "Howell pool rule function already exists."
        )
        return

    marker = (
        "# ============================================================\n"
        "# OPTIONAL SOURCE REGISTRY HELPERS\n"
        "# ============================================================\n"
    )

    if marker not in text:
        raise RuntimeError(
            "Could not find zoning_intelligence helper marker."
        )

    function = r'''
# ============================================================
# HOWELL TOWNSHIP — POOL REQUIREMENTS
# ============================================================

def _build_howell_pool_requirements() -> list[dict[str, Any]]:
    """
    Official Howell Township pool requirements.

    These are project-specific municipal requirements and are
    intentionally kept separate from HD-4 bulk standards.

    Sources:
        - Howell Township In-ground Swimming Pool checklist
        - Howell Township Land Use FAQ
    """

    return [
        {
            "requirement": (
                "Minimum pool setback"
            ),
            "value": "10 ft minimum",
            "applies_to": (
                "Pool / pool improvements"
            ),
            "basis": (
                "Howell Township states that pool setbacks "
                "are 10 ft to side and rear property lines."
            ),
            "source": (
                "Howell Township Land Use FAQ"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/m/faq"
            ),
            "authoritative": True,
            "verification": (
                "Confirm the proposed location against the "
                "actual surveyed property lines and applicable "
                "front-yard restrictions."
            ),
        },
        {
            "requirement": (
                "Pool equipment setback"
            ),
            "value": "10 ft minimum",
            "applies_to": (
                "Pool equipment"
            ),
            "basis": (
                "Howell Township's in-ground pool checklist "
                "requires pool equipment to be at least 10 ft "
                "from any property line."
            ),
            "source": (
                "Howell Township In-ground Swimming Pool Checklist"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/DocumentCenter/View/431"
            ),
            "authoritative": True,
            "verification": (
                "Show equipment location and measured setback "
                "on the site plan."
            ),
        },
        {
            "requirement": (
                "Waterline setback"
            ),
            "value": "10 ft minimum",
            "applies_to": (
                "Pool waterline"
            ),
            "basis": (
                "Howell requires the waterline to be at least "
                "10 ft from a property line, subject to the "
                "Township's stated measurement condition where "
                "an adjacent walkway, patio, or deck is present."
            ),
            "source": (
                "Howell Township In-ground Swimming Pool Checklist"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/DocumentCenter/View/431"
            ),
            "authoritative": True,
            "verification": (
                "Measure from the applicable edge identified "
                "by the Township checklist."
            ),
        },
        {
            "requirement": (
                "Grade-change restriction"
            ),
            "value": (
                "No grade change within 5 ft of property line"
            ),
            "applies_to": (
                "Pool site work"
            ),
            "basis": (
                "Howell's in-ground pool checklist prohibits "
                "grade changes within 5 ft of a property line."
            ),
            "source": (
                "Howell Township In-ground Swimming Pool Checklist"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/DocumentCenter/View/431"
            ),
            "authoritative": True,
            "verification": (
                "Existing and proposed grades should be shown "
                "on the engineering/site plan."
            ),
        },
        {
            "requirement": (
                "Distance from residential dwelling"
            ),
            "value": "6 ft minimum",
            "applies_to": (
                "Pool adjacent to residential dwelling"
            ),
            "basis": (
                "Howell's checklist requires the pool to be "
                "at least 6 ft from the residential dwelling."
            ),
            "source": (
                "Howell Township In-ground Swimming Pool Checklist"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/DocumentCenter/View/431"
            ),
            "authoritative": True,
            "verification": (
                "If the pool is within 12 ft of an adjacent "
                "structure, provide the required cross-section "
                "drawings."
            ),
        },
        {
            "requirement": (
                "Backwash discharge"
            ),
            "value": (
                "Show location on plan"
            ),
            "applies_to": (
                "In-ground pool"
            ),
            "basis": (
                "Howell requires the pool backwash discharge "
                "location to be graphically depicted on the plan."
            ),
            "source": (
                "Howell Township In-ground Swimming Pool Checklist"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/DocumentCenter/View/431"
            ),
            "authoritative": True,
            "verification": (
                "Coordinate the discharge location with the "
                "site drainage design and applicable approvals."
            ),
        },
        {
            "requirement": (
                "Commercial property land-use review"
            ),
            "value": (
                "Site-plan approval required; streamlined "
                "Conditionally Exempt Site Plan may be possible "
                "if criteria are satisfied"
            ),
            "applies_to": (
                "Commercial property improvements"
            ),
            "basis": (
                "Howell states that any improvement on a "
                "commercial property requires site-plan approval "
                "through the Planning or Zoning Board, with a "
                "possible Conditionally Exempt Site Plan route "
                "for qualifying minor improvements."
            ),
            "source": (
                "Howell Township Land Use FAQ"
            ),
            "source_url": (
                "https://www.twp.howell.nj.us/m/faq"
            ),
            "authoritative": True,
            "verification": (
                "Determine whether the proposed pool qualifies "
                "for the Conditionally Exempt Site Plan criteria "
                "under Chapter 188-110."
            ),
        },
    ]


'''

    text = text.replace(
        marker,
        function + marker,
        1,
    )

    ZONING.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Added Howell pool requirements."
    )


def add_howell_branch() -> None:
    text = ZONING.read_text(
        encoding="utf-8"
    )

    marker = (
        "        project_requirements: list[\n"
        "            dict[str, Any]\n"
        "        ] = []\n"
    )

    if marker not in text:
        raise RuntimeError(
            "Could not find project_requirements block."
        )

    branch = '''
        if (
            config["canonical_name"]
            == "Howell Township"
            and project == "pool"
        ):
            project_requirements = (
                _build_howell_pool_requirements()
            )
'''

    # Insert only once immediately after the first empty
    # project_requirements declaration.
    if (
        "== \"Howell Township\"" not in text
    ):
        text = text.replace(
            marker,
            marker + branch,
            1,
        )

    ZONING.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Connected Howell pool rules to the zoning engine."
    )


def update_main_merge() -> None:
    text = MAIN.read_text(
        encoding="utf-8"
    )

    old = '''        if resolved_district != "R-20":

            # Never apply R-20 residential requirements to
            # another zoning district.
            merged[
                "bulk_requirements"
            ] = []

            merged[
                "project_requirements"
            ] = []
'''

    new = '''        if resolved_district != "R-20":

            # Never apply R-20 residential requirements to
            # another zoning district.
            merged[
                "bulk_requirements"
            ] = []

            # Preserve project-specific requirements when the
            # municipal engine has an authoritative rule set
            # for the resolved district/project combination.
            #
            # Howell HD-4 pool requirements are municipal
            # project rules and are therefore retained here.
            if not (
                merged.get(
                    "municipality"
                ) == "Howell Township"
                and resolved_district == "HD-4"
                and merged.get(
                    "project_requirements"
                )
            ):
                merged[
                    "project_requirements"
                ] = []
'''

    if old not in text:
        raise RuntimeError(
            "Could not find NON-R-20 merge block in main.py."
        )

    text = text.replace(
        old,
        new,
        1,
    )

    # Replace the old misleading verification message.
    old_message = '''                    (
                        "Project-specific residential pool "
                        "requirements were intentionally withheld "
                        "because the resolved zoning district is "
                        f"{resolved_district}."
                    ),
'''

    new_message = '''                    (
                        "Residential R-20 pool requirements were "
                        "not applied because the resolved parcel "
                        "is in the "
                        f"{resolved_district} zoning district."
                    ),
'''

    if old_message in text:
        text = text.replace(
            old_message,
            new_message,
            1,
        )

    old_pending = '''                    (
                        "District-specific bulk and project rules "
                        "for the resolved zoning district must be "
                        "retrieved from the applicable authoritative "
                        "municipal source before being reported."
                    ),
'''

    new_pending = '''                    (
                        "HD-4 bulk/dimensional standards have not "
                        "yet been loaded into MIDRA from the current "
                        "Howell Township Bulk Standards Table II."
                    ),
'''

    if old_pending in text:
        text = text.replace(
            old_pending,
            new_pending,
            1,
        )

    # If Howell has project requirements, make the confidence
    # accurately reflect that project rules are available even
    # though district bulk standards remain pending.
    confidence_old = '''            merged["confidence"] = (
                "PARCEL_ZONING_RESOLVED_RULES_PENDING"
            )
'''

    confidence_new = '''            if (
                merged.get(
                    "municipality"
                ) == "Howell Township"
                and resolved_district == "HD-4"
                and merged.get(
                    "project_requirements"
                )
            ):
                merged["confidence"] = (
                    "PARCEL_ZONING_RESOLVED_PROJECT_RULES_AVAILABLE"
                )
            else:
                merged["confidence"] = (
                    "PARCEL_ZONING_RESOLVED_RULES_PENDING"
                )
'''

    if confidence_old in text:
        text = text.replace(
            confidence_old,
            confidence_new,
            1,
        )

    MAIN.write_text(
        text,
        encoding="utf-8",
    )

    print(
        "Updated property-specific zoning merge."
    )


def main() -> None:
    print("")
    print("==============================================")
    print("MIDRA Howell HD-4 / pool rules upgrade")
    print("==============================================")
    print("")

    backup(ZONING)
    backup(MAIN)

    add_howell_rule_function()
    add_howell_branch()
    update_main_merge()

    print("")
    print("Running syntax checks...")
    print("")

    import py_compile

    py_compile.compile(
        str(ZONING),
        doraise=True,
    )

    py_compile.compile(
        str(MAIN),
        doraise=True,
    )

    print("")
    print("==============================================")
    print("SUCCESS")
    print("Howell project rules are installed.")
    print("==============================================")
    print("")


if __name__ == "__main__":
    main()