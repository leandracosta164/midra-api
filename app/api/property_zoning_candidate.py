"""Controlled Property zoning-candidate geometry API.

This endpoint exposes GIS geometry from MIDRA's existing dynamic zoning candidate path.
It does not convert candidate geometry into an authoritative zoning determination.
"""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.services.zoning_spatial_bridge import resolve_dynamic_spatial_zoning_candidate


router = APIRouter(
    prefix="/property/zoning-candidate",
    tags=["property-zoning-candidate"],
)


def _get_db() -> Generator[Any, None, None]:
    # Lazy import keeps this API module independently testable without creating
    # a database engine at import time.
    from app.db.session import get_db
    yield from get_db()


class ZoningCandidateGeometryRequest(BaseModel):
    municipality: str = Field(min_length=2, max_length=150)
    block: str = Field(min_length=1, max_length=80)
    lot: str = Field(min_length=1, max_length=80)
    parcel_geometry: dict[str, Any]


@router.post("/geometry")
def zoning_candidate_geometry(
    payload: ZoningCandidateGeometryRequest,
    db: Any = Depends(_get_db),
) -> dict[str, Any]:
    geometry = payload.parcel_geometry
    rings = geometry.get("rings") if isinstance(geometry, dict) else None
    if not isinstance(rings, list) or not rings:
        return {
            "status": "VERIFY",
            "candidate": None,
            "reason": "PARCEL_GEOMETRY_NOT_RESOLVED",
            "candidate_only": True,
            "professional_boundary": {
                "definitive": False,
                "message": (
                    "Zoning geometry cannot be screened without resolved parcel "
                    "reference geometry. MIDRA will not invent a parcel or zoning boundary."
                ),
            },
        }

    result = resolve_dynamic_spatial_zoning_candidate(
        municipality=payload.municipality,
        block=payload.block,
        lot=payload.lot,
        geometry=geometry,
        db=db,
    )

    candidate = result if result.get("status") == "ZONING_CANDIDATE_RESOLVED" else None

    return {
        "status": (
            "CANDIDATE_GEOMETRY_AVAILABLE"
            if candidate and (candidate.get("record") or {}).get("mapped_geometries")
            else "VERIFY"
        ),
        "candidate": candidate,
        "reason": None if candidate else result.get("reason"),
        "candidate_only": True,
        "professional_boundary": {
            "definitive": False,
            "message": (
                "Mapped zoning polygons are candidate GIS evidence only. Geometry alone "
                "does not establish authoritative zoning, legal control, development "
                "entitlement, or a professional determination."
            ),
        },
    }
