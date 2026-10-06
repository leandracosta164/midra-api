"""Public dynamic statewide Property Intelligence overlay.

This route exposes MIDRA's existing dynamic zoning/source-discovery chain as
supplemental evidence. It never replaces established zoning or professional
review boundaries.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.dynamic_property_analysis import analyze_dynamic_property
from app.services.property_dynamic_source_trust import build_dynamic_source_trust_summary


router = APIRouter(
    prefix="/property/dynamic-intelligence",
    tags=["property-dynamic-intelligence"],
)


def _get_db() -> Generator[Any, None, None]:
    # Lazy import keeps this public evidence route independently testable.
    from app.db.session import get_db
    yield from get_db()


class DynamicPropertyIntelligenceRequest(BaseModel):
    municipality: str = Field(min_length=2, max_length=150)
    block: str = Field(min_length=1, max_length=80)
    lot: str = Field(min_length=1, max_length=80)
    parcel_geometry: dict[str, Any]
    project_goal: str = Field(default="other", min_length=2, max_length=200)


@router.post("/analyze")
def dynamic_property_intelligence(
    payload: DynamicPropertyIntelligenceRequest,
    db: Any = Depends(_get_db),
) -> dict[str, Any]:
    geometry = payload.parcel_geometry
    rings = geometry.get("rings") if isinstance(geometry, dict) else None
    if not isinstance(rings, list) or not rings:
        return {
            "status": "VERIFY",
            "dynamic_promotable": False,
            "reason": "PARCEL_GEOMETRY_OR_IDENTITY_MISSING",
            "professional_boundary": {
                "definitive": False,
                "message": (
                    "Dynamic statewide intelligence requires resolved parcel identity "
                    "and reference geometry. MIDRA will not invent missing zoning, "
                    "project rules, or approval evidence."
                ),
            },
        }

    try:
        result = analyze_dynamic_property(
            municipality=payload.municipality,
            block=payload.block,
            lot=payload.lot,
            geometry=geometry,
            project_goal=payload.project_goal,
            db=db,
        )
    except Exception as exc:
        return {
            "status": "VERIFY",
            "dynamic_promotable": False,
            "reason": "DYNAMIC_INTELLIGENCE_UNAVAILABLE",
            "error_type": exc.__class__.__name__,
            "professional_boundary": {
                "definitive": False,
                "message": (
                    "Dynamic source discovery was unavailable. Existing established "
                    "Property Intelligence remains unchanged and MIDRA will not infer "
                    "missing zoning or regulatory conclusions."
                ),
            },
        }

    return {
        **result,
        "source_trust_summary": build_dynamic_source_trust_summary(result),
        "professional_boundary": {
            "definitive": False,
            "message": (
                "Dynamic zoning, project-rule, and approval evidence is supplemental "
                "MIDRA Analysis. Candidate evidence is not promoted unless the existing "
                "authority and legal-control guards explicitly permit promotion, and it "
                "is never an engineer review or acceptance."
            ),
        },
    }
