from __future__ import annotations

from typing import Any

from app.services.municipality_source_discovery import discover_municipality_sources


# Stage B — municipality source registry.
#
# This registry identifies authoritative municipal zoning sources.
# It does NOT assert that a parcel's zoning district has been resolved,
# and it does NOT make project rules applicable.
#
# Seeded from official municipal/state sources reviewed for Stage B:
# - NJ DCA Zoning Information Directory / Community Asset Map
# - Howell Township official Land Use / Township Maps pages
# - Marlboro Township official Zoning/Code Enforcement page and zoning map
# - Newark official Division of Planning & Zoning page and zoning ordinance
#
# Source freshness must be reviewed before relying on a source for a
# property-specific legal conclusion.

MUNICIPALITY_SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "howell township": {
        "canonical_name": "Howell Township",
        "county": "Monmouth County",
        "state": "New Jersey",
        "source_status": "OFFICIAL_SOURCES_IDENTIFIED",
        "sources": {
            "zoning_page": {
                "url": "https://www.twp.howell.nj.us/134/Land-Use",
                "source_type": "municipal_land_use_page",
                "authoritative": True,
            },
            "zoning_map": {
                "url": "https://www.twp.howell.nj.us/452/Township-Maps",
                "source_type": "municipal_zoning_map_index",
                "authoritative": True,
                "reported_update": "May 2024",
            },
            "zoning_faq": {
                "url": "https://www.twp.howell.nj.us/m/faq",
                "source_type": "municipal_land_use_faq",
                "authoritative": True,
            },
        },
        "coverage_notes": [
            "Official municipal land-use page identifies zoning/land-use functions and applications.",
            "Official township maps page identifies the zoning map and reports it updated May 2024.",
            "Source identification does not establish parcel-specific zoning.",
        ],
    },
    "marlboro township": {
        "canonical_name": "Marlboro Township",
        "county": "Monmouth County",
        "state": "New Jersey",
        "source_status": "OFFICIAL_SOURCES_IDENTIFIED",
        "sources": {
            "zoning_page": {
                "url": "https://www.marlboro-nj.gov/Departments/zoning-code-enforcement-division",
                "source_type": "municipal_zoning_code_enforcement_page",
                "authoritative": True,
            },
            "zoning_map": {
                "url": "https://www.marlboro-nj.gov/_Content/pdf/ZoningMap.pdf",
                "source_type": "municipal_zoning_map",
                "authoritative": True,
            },
            "zoning_portal": {
                "url": "https://www.marlboro-nj.gov/pages/online-zoning-portal",
                "source_type": "municipal_zoning_portal",
                "authoritative": True,
            },
        },
        "code_reference": {
            "platform": "eCode360",
            "url": "https://ecode360.com/12875022",
            "source_type": "municipal_land_use_code",
            "authoritative": True,
        },
        "coverage_notes": [
            "Official municipal zoning/code-enforcement page identifies zoning ordinance enforcement.",
            "Official municipal zoning map is separately registered.",
            "Source identification does not establish parcel-specific zoning.",
        ],
    },
    "newark city": {
        "canonical_name": "Newark City",
        "county": "Essex County",
        "state": "New Jersey",
        "source_status": "OFFICIAL_SOURCES_IDENTIFIED",
        "sources": {
            "planning_zoning_page": {
                "url": "https://www.newarknj.gov/257/Division-of-Planning-Zoning",
                "source_type": "municipal_planning_zoning_page",
                "authoritative": True,
            },
            "zoning_ordinance": {
                "url": "https://www.newarknj.gov/DocumentCenter/View/999/Zoning-Ordinance-PDF",
                "source_type": "municipal_zoning_ordinance",
                "authoritative": True,
            },
            "economic_housing_development": {
                "url": "https://www.newarknj.gov/172/Economic-Housing-Development",
                "source_type": "municipal_department_page",
                "authoritative": True,
            },
        },
        "coverage_notes": [
            "Official city page provides an interactive zoning map and zoning/land-use regulations.",
            "Newark is intentionally registered here as a source-identified municipality, not as a municipality with parcel-level zoning support.",
        ],
    },
}


ALIASES: dict[str, str] = {
    "howell": "howell township",
    "howell twp": "howell township",
    "howell township": "howell township",
    "marlboro": "marlboro township",
    "marlboro twp": "marlboro township",
    "marlboro township": "marlboro township",
    "newark": "newark city",
    "newark city": "newark city",
}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def resolve_municipality_source(
    municipality: str | None,
) -> dict[str, Any]:
    requested = str(municipality or "").strip()
    key = _normalize(requested)
    canonical_key = ALIASES.get(key, key)
    record = MUNICIPALITY_SOURCE_REGISTRY.get(canonical_key)

    if not record:
        discovered = discover_municipality_sources(requested)
        if discovered.get("registered"):
            return discovered
        return {
            "status": "SOURCE_REGISTRY_NOT_FOUND",
            "registered": False,
            "municipality": requested or None,
            "canonical_name": None,
            "sources": {},
            "notes": [
                "Static source registry does not currently contain this municipality.",
                "Dynamic DCA source discovery did not produce a usable source record.",
                "This does not establish that authoritative municipal zoning sources do not exist.",
            ],
        }

    return {
        "status": "OFFICIAL_SOURCES_IDENTIFIED",
        "registered": True,
        "municipality": requested or record["canonical_name"],
        "canonical_name": record["canonical_name"],
        "county": record["county"],
        "state": record["state"],
        "source_status": record["source_status"],
        "sources": record.get("sources", {}),
        "code_reference": record.get("code_reference"),
        "coverage_notes": record.get("coverage_notes", []),
        "notes": [
            "Stage B identifies authoritative municipal zoning sources.",
            "Source identification does not establish parcel-specific zoning.",
            "Source identification does not establish project-rule applicability.",
        ],
    }


def build_municipality_source_registry(
    municipality: str | None,
) -> dict[str, Any]:
    """Return the Stage B source-registry result for a municipality."""
    return resolve_municipality_source(municipality)
