from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SERVICES = ROOT / "app" / "services"

ZONING_INTELLIGENCE = SERVICES / "zoning_intelligence.py"
ZONING_RESOLUTION = SERVICES / "zoning_resolution.py"


def backup(path: Path) -> None:
    backup_path = path.with_suffix(path.suffix + ".before-howell")
    shutil.copy2(path, backup_path)
    print(f"Backup: {backup_path}")


def patch_zoning_intelligence() -> None:
    path = ZONING_INTELLIGENCE
    text = path.read_text(encoding="utf-8")

    marker = 'MUNICIPALITY_SOURCES: dict[str, dict[str, Any]] = {\n'

    if marker not in text:
        raise RuntimeError(
            "Could not find MUNICIPALITY_SOURCES registry."
        )

    if '"howell township": {' in text:
        print("Howell Township already exists in zoning_intelligence.py")
        return

    insertion = '''    "howell township": {
        "canonical_name": "Howell Township",
        "county": "Monmouth County",
        "state": "New Jersey",

        "ecode": {
            "enabled": False,
            "url": None,
            "description": (
                "Howell Township Chapter 188 Land Use Ordinance."
            ),
        },

        "official": {
            "enabled": True,
            "base_url": "https://www.twp.howell.nj.us/",
            "zoning_page": (
                "https://www.twp.howell.nj.us/134/Land-Use"
            ),
            "zoning_map": (
                "https://www.twp.howell.nj.us/DocumentCenter/"
                "View/2420/Zoning-Map-Updated-May-2024"
            ),
        },

        "code_sections": {
            "land_use": "Chapter 188",
            "hd4": "§188-78.3",
            "permitted_uses": "Schedule 1",
            "bulk_standards": "Bulk Standards Table II",
            "pools": "Howell Township Land Use FAQ",
        },
    },

'''

    text = text.replace(
        marker,
        marker + insertion,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("Updated zoning_intelligence.py")


def patch_zoning_resolution() -> None:
    path = ZONING_RESOLUTION
    text = path.read_text(encoding="utf-8")

    marker = (
        "# ============================================================\n"
        "# MAIN RESOLVER\n"
        "# ============================================================\n"
    )

    if marker not in text:
        raise RuntimeError(
            "Could not find zoning resolver main-resolver marker."
        )

    if "HOWELL_HD4_PARCELS" in text:
        print("Howell parcel evidence already exists.")
        return

    insertion = '''# ============================================================
# HOWELL HD-4 PARCELS
# ============================================================

#
# These parcels are explicitly identified in Howell Township's
# adopted zoning legislation as being rezoned from HD-2 to HD-4.
#
# This is NOT a general Howell Township -> HD-4 assumption.
#
# The evidence is parcel-specific.
#
# Primary parcel-specific source:
# Howell Township Ordinance O-22-29
#
# Current map cross-check:
# Howell Township Zoning Map, updated May 2024
#
# ============================================================

HOWELL_HD4_PARCELS: dict[
    tuple[str, str],
    dict[str, Any],
] = {

    ("177", "16.01"): {
        "current_district": "HD-4",
        "previous_district": "HD-2",
        "source_ordinance": "O-22-29",
        "source_description": (
            "Howell Township adopted Ordinance O-22-29 "
            "rezoning Block 177 Lot 16.01 from HD-2 to HD-4."
        ),
        "zoning_map_source": (
            "Howell Township Zoning Map, updated May 2024"
        ),
    },
}


'''

    text = text.replace(
        marker,
        insertion + marker,
        1,
    )

    # Insert Howell branch immediately before the Marlboro branch.
    marlboro_marker = (
        '    # ========================================================\n'
        '    # MARLBORO\n'
        '    # ========================================================\n'
    )

    if marlboro_marker not in text:
        raise RuntimeError(
            "Could not find Marlboro resolver branch."
        )

    howell_branch = '''    # ========================================================
    # HOWELL TOWNSHIP
    # ========================================================

    if normalized_municipality == (
        "howell township"
    ):

        key = (
            block,
            lot,
        )

        evidence = HOWELL_HD4_PARCELS.get(
            key
        )

        if evidence:

            return {
                "status": "ZONING_RESOLVED",

                "zoning_district": "HD-4",

                "zoning_name": (
                    "Highway Development 4"
                ),

                "source": {
                    "municipality": (
                        "Howell Township"
                    ),
                    "source_type": (
                        "Official Municipal Ordinance / "
                        "Official Zoning Map"
                    ),
                    "url": (
                        "https://www.twp.howell.nj.us/"
                        "DocumentCenter/View/7437/"
                        "O-22-29-ADOPT-Rezone-to-HD-4-FINAL"
                    ),
                    "description": (
                        evidence[
                            "source_description"
                        ]
                    ),
                    "authoritative": True,
                },

                "zoning_map_source": {
                    "source_type": (
                        "Official Municipal Zoning Map"
                    ),
                    "url": (
                        "https://www.twp.howell.nj.us/"
                        "DocumentCenter/View/2420/"
                        "Zoning-Map-Updated-May-2024"
                    ),
                    "authoritative": True,
                },

                "parcel_reference": {
                    "block": block,
                    "lot": lot,
                    "pams_pin": parcel.get(
                        "pams_pin"
                    ),
                },

                "parcel_evidence": {
                    "previous_district": (
                        evidence[
                            "previous_district"
                        ]
                    ),
                    "resolved_district": (
                        evidence[
                            "current_district"
                        ]
                    ),
                    "ordinance": (
                        evidence[
                            "source_ordinance"
                        ]
                    ),
                },

                "source_section": (
                    "Howell Township Ordinance O-22-29"
                ),

                "retrieved_at": retrieved_at,

                "confidence": (
                    "OFFICIAL_PARCEL_SPECIFIC"
                ),

                "verification_items": [
                    (
                        "The zoning district is supported by "
                        "Howell Township parcel-specific "
                        "rezoning evidence for Block 177 "
                        "Lot 16.01."
                    ),
                    (
                        "The current Howell Township zoning map "
                        "is identified as an authoritative "
                        "municipal map source."
                    ),
                    (
                        "Later amendments, variances, site plans, "
                        "and other property-specific approvals "
                        "should still be verified before design "
                        "or permitting."
                    ),
                ],

                "notes": [
                    (
                        "This is a parcel-specific zoning result."
                    ),
                    (
                        "MIDRA does not infer HD-4 merely from "
                        "the property being located in Howell "
                        "Township."
                    ),
                    (
                        "The parcel was identified as Block 177 "
                        "Lot 16.01 by the NJ statewide parcel "
                        "service."
                    ),
                ],
            }


        return {
            "status": "ZONING_NOT_RESOLVED",

            "zoning_district": "VERIFY",

            "source": {
                "municipality": (
                    "Howell Township"
                ),
                "source_type": (
                    "Official Municipal Zoning Sources"
                ),
                "url": (
                    "https://www.twp.howell.nj.us/"
                    "DocumentCenter/View/2420/"
                    "Zoning-Map-Updated-May-2024"
                ),
                "description": (
                    "Howell Township has an authoritative "
                    "municipal zoning map and zoning ordinance, "
                    "but MIDRA does not have parcel-specific "
                    "evidence for this Block/Lot."
                ),
                "authoritative": True,
            },

            "zoning_map_source": {
                "source_type": (
                    "Official Municipal Zoning Map"
                ),
                "url": (
                    "https://www.twp.howell.nj.us/"
                    "DocumentCenter/View/2420/"
                    "Zoning-Map-Updated-May-2024"
                ),
                "authoritative": True,
            },

            "parcel_reference": {
                "block": block,
                "lot": lot,
                "pams_pin": parcel.get(
                    "pams_pin"
                ),
            },

            "retrieved_at": retrieved_at,

            "confidence": (
                "PARCEL_ZONING_NOT_YET_RESOLVED"
            ),

            "verification_items": [
                (
                    "Howell Township has an authoritative "
                    "municipal zoning source."
                ),
                (
                    "MIDRA does not have sufficient "
                    "parcel-specific zoning evidence for "
                    "this Block/Lot."
                ),
                (
                    "Do not infer the zoning district from "
                    "nearby parcels or from the municipality "
                    "alone."
                ),
            ],

            "notes": [
                (
                    "The official Howell zoning map remains "
                    "the controlling municipal map source."
                ),
            ],
        }


'''

    text = text.replace(
        marlboro_marker,
        howell_branch + marlboro_marker,
        1,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    print("Updated zoning_resolution.py")


def main() -> None:
    print("")
    print("==============================================")
    print("MIDRA Howell Township zoning upgrade")
    print("==============================================")
    print("")

    backup(ZONING_INTELLIGENCE)
    backup(ZONING_RESOLUTION)

    patch_zoning_intelligence()
    patch_zoning_resolution()

    print("")
    print("Howell zoning upgrade complete.")
    print("")


if __name__ == "__main__":
    main()