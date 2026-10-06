"""
MIDRA Engineering
Property Zoning Resolution

Purpose
-------
Resolve a verified New Jersey parcel to a zoning district
using authoritative municipal parcel-specific evidence.

This service is intentionally conservative.

It does NOT infer a zoning district merely because a
municipality has a particular residential district.

If authoritative parcel-specific zoning evidence is not
available, the result is VERIFY.

Current supported parcel-specific evidence:
Marlboro Township, New Jersey.

The Marlboro source identifies specific Block/Lot parcels
within the Community Facilities (CF) District.

Long-term architecture:
    Parcel
        â†“
    Municipal zoning GIS
        â†“
    Zoning polygon
        â†“
    District

When a municipality does not provide machine-readable zoning
GIS, official ordinance/resolution evidence may be used when
it explicitly identifies the parcel and zoning district.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ============================================================
# AUTHORITATIVE SOURCES
# ============================================================

MARLBORO_CF_SOURCE_URL = (
    "https://www.marlboro-nj.gov/_Content/pdf/"
    "Res-2019-315-Ord%202019-14.pdf"
)

MARLBORO_ZONING_MAP_URL = (
    "https://www.marlboro-nj.gov/_Content/pdf/"
    "ZoningMap.pdf"
)

MARLBORO_ZONING_PAGE_URL = (
    "https://www.marlboro-nj.gov/Departments/"
    "zoning-code-enforcement-division"
)


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _clean(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _normalize_municipality(
    value: str | None,
) -> str:

    value = (
        value or ""
    ).strip().lower()

    replacements = {
        "marlboro": "marlboro township",
        "marlboro twp": "marlboro township",
        "marlboro township": "marlboro township",

        "howell": "howell township",
        "howell twp": "howell township",
        "howell township": "howell township",
    }

    return replacements.get(
        value,
        value,
    )

def _normalize_block_lot(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text.upper()


# ============================================================
# MARLBORO COMMUNITY FACILITIES PARCELS
# ============================================================

#
# These parcels are explicitly identified in Marlboro
# Township's official zoning legislation as Community
# Facilities District parcels.
#
# This is NOT a general municipality â†’ CF assumption.
#
# It is a parcel-specific evidence set.
#
# Source:
# Resolution 2019-315 / Ordinance 2019-14
#
# ============================================================

MARLBORO_CF_PARCELS: dict[
    tuple[str, str],
    dict[str, Any],
] = {

    ("225", "199"): {
        "facility": "Marlboro High School",
        "acreage": 44.2,
    },

    ("253", "34"): {
        "facility": (
            "Marlboro Middle School and fields"
        ),
        "acreage": 30.8,
    },

    ("253", "35.02"): {
        "facility": "Library",
        "acreage": 4.1,
    },

    ("253", "37.01"): {
        "facility": "Municipal Complex",
        "acreage": 17.6,
    },

    ("253", "38"): {
        "facility": "Board of Ed Building",
        "acreage": 2.0,
    },

    ("253", "39"): {
        "facility": "Bus Storage",
        "acreage": 4.0,
    },

    ("255", "68"): {
        "facility": "Vacant Land",
        "acreage": 0.3,
    },

    ("270", "59"): {
        "facility": "Vacant Land",
        "acreage": 6.8,
    },

    ("299", "20"): {
        "facility": "Parking Area",
        "acreage": 7.3,
    },

    ("299", "160"): {
        "facility": "Asher Holmes Elementary",
        "acreage": 30.4,
    },

    ("299", "177"): {
        "facility": (
            "Robertsville Elementary / Tennis Courts"
        ),
        "acreage": 2.9,
    },

    ("305", "181"): {
        "facility": "Pumping Station",
        "acreage": 0.5,
    },

    ("312", "159"): {
        "facility": "First Aid Station",
        "acreage": 5.3,
    },

    ("312", "160"): {
        "facility": "Vacant Land",
        "acreage": 7.5,
    },

    ("335", "5"): {
        "facility": "Schechter School",
        "acreage": 0.5,
    },

    ("339", "90"): {
        "facility": "Dugan Elementary",
        "acreage": 0.5,
    },

    ("360.02", "15.01"): {
        "facility": "Pump Station",
        "acreage": 0.2,
    },

    ("360.02", "18.63"): {
        "facility": "Pump Station",
        "acreage": 0.3,
    },

    ("415", "32.02"): {
        "facility": "Pump Station",
        "acreage": 0.3,
    },
}


# ============================================================
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


# ============================================================
# MAIN RESOLVER
# ============================================================

def resolve_property_zoning(
    *,
    municipality: str | None,
    parcel: dict[str, Any] | None,
) -> dict[str, Any]:

    retrieved_at = _utc_now()

    normalized_municipality = (
        _normalize_municipality(
            municipality
        )
    )

    if not parcel:

        return {
            "status": "PARCEL_REQUIRED",

            "zoning_district": "VERIFY",

            "source": {
                "municipality": municipality,
                "source_type": "NOT_RESOLVED",
                "url": None,
                "description": (
                    "A verified parcel is required before "
                    "property-specific zoning can be assigned."
                ),
                "authoritative": False,
            },

            "retrieved_at": retrieved_at,

            "confidence": "PARCEL_REQUIRED",

            "verification_items": [
                (
                    "The property has not been resolved to "
                    "a verified parcel."
                ),
                (
                    "Property-specific zoning cannot be "
                    "safely determined."
                ),
            ],

            "notes": [],
        }

    block = _normalize_block_lot(
        parcel.get(
            "block"
        )
    )

    lot = _normalize_block_lot(
        parcel.get(
            "lot"
        )
    )

    if not block or not lot:

        return {
            "status": "BLOCK_LOT_REQUIRED",

            "zoning_district": "VERIFY",

            "source": {
                "municipality": municipality,
                "source_type": "PARCEL",
                "url": None,
                "description": (
                    "Block and lot information are required "
                    "for the available parcel-specific zoning "
                    "evidence."
                ),
                "authoritative": False,
            },

            "parcel_reference": {
                "block": block,
                "lot": lot,
                "pams_pin": parcel.get(
                    "pams_pin"
                ),
            },

            "retrieved_at": retrieved_at,

            "confidence": "BLOCK_LOT_REQUIRED",

            "verification_items": [
                (
                    "The resolved parcel does not contain "
                    "usable Block/Lot identifiers."
                ),
            ],

            "notes": [],
        }

    # ========================================================
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


    # ========================================================
    # MARLBORO
    # ========================================================

    if normalized_municipality == (
        "marlboro township"
    ):

        key = (
            block,
            lot,
        )

        evidence = MARLBORO_CF_PARCELS.get(
            key
        )

        if evidence:

            return {
                "status": "ZONING_RESOLVED",

                "zoning_district": "CF",

                "zoning_name": (
                    "Community Facilities"
                ),

                "source": {
                    "municipality": (
                        "Marlboro Township"
                    ),

                    "source_type": (
                        "Official Municipal Ordinance / Resolution"
                    ),

                    "url": (
                        MARLBORO_CF_SOURCE_URL
                    ),

                    "description": (
                        "Marlboro Township official zoning "
                        "legislation identifying the parcel "
                        "within the Community Facilities "
                        "District."
                    ),

                    "authoritative": True,
                },

                "zoning_map_source": {
                    "source_type": (
                        "Official Municipal Zoning Map"
                    ),

                    "url": (
                        MARLBORO_ZONING_MAP_URL
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
                    "facility": evidence.get(
                        "facility"
                    ),

                    "listed_acreage": evidence.get(
                        "acreage"
                    ),
                },

                "source_section": (
                    "Community Facilities District"
                ),

                "retrieved_at": retrieved_at,

                "confidence": (
                    "OFFICIAL_PARCEL_SPECIFIC"
                ),

                "verification_items": [
                    (
                        "Zoning district is supported by "
                        "official Marlboro Township "
                        "parcel-specific zoning legislation."
                    ),
                    (
                        "Current zoning, subsequent amendments, "
                        "and site-specific approvals should "
                        "still be verified before design or "
                        "permitting."
                    ),
                ],

                "notes": [
                    (
                        "This result is parcel-specific."
                    ),
                    (
                        "MIDRA does not infer CF merely from "
                        "the municipality being Marlboro."
                    ),
                ],
            }

    # ========================================================
    # NO AUTHORITATIVE PARCEL-SPECIFIC RESULT
    # ========================================================

    return {
        "status": "ZONING_NOT_RESOLVED",

        "zoning_district": "VERIFY",

        "source": {
            "municipality": municipality,

            "source_type": (
                "Official Municipal Zoning Sources"
            ),

            "url": (
                MARLBORO_ZONING_PAGE_URL
                if normalized_municipality
                == "marlboro township"
                else None
            ),

            "description": (
                "The municipality has an authoritative "
                "zoning source, but MIDRA does not yet have "
                "sufficient parcel-specific evidence to "
                "assign the zoning district automatically."
            ),

            "authoritative": True,
        },

        "zoning_map_source": (
            {
                "source_type": (
                    "Official Municipal Zoning Map"
                ),

                "url": MARLBORO_ZONING_MAP_URL,

                "authoritative": True,
            }
            if normalized_municipality
            == "marlboro township"
            else None
        ),

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
                "The parcel was successfully resolved, "
                "but MIDRA does not yet have authoritative "
                "parcel-specific zoning evidence for this "
                "Block/Lot."
            ),
            (
                "Do not infer the zoning district from "
                "nearby parcels or from the municipality "
                "alone."
            ),
        ],

        "notes": [
            (
                "The official municipal zoning map remains "
                "the controlling map source."
            ),
        ],
    }
    
