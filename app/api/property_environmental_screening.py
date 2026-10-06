"""Controlled Property environmental-screening API.

This endpoint exposes authoritative-source GIS screening without converting screening
evidence into a regulatory determination.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any

from app.services.njdep_environmental_screening import (
    screen_njdep_wetlands_point,
    screen_njdep_fema_flood_point,
    screen_njdep_wetlands_parcel_geometry,
    screen_njdep_fema_flood_parcel_geometry,
)

router = APIRouter(prefix="/property/environmental-screening", tags=["property-environmental-screening"])

class EnvironmentalScreeningRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    parcel_geometry: dict[str, Any] | None = None

@router.post("/wetlands")
def screen_wetlands(payload: EnvironmentalScreeningRequest) -> dict:
    return {
        "kind": "wetlands",
        "screening": (
            screen_njdep_wetlands_parcel_geometry(
                parcel_geometry=payload.parcel_geometry,
            )
            if isinstance(payload.parcel_geometry, dict) and payload.parcel_geometry
            else screen_njdep_wetlands_point(
                longitude=payload.longitude,
                latitude=payload.latitude,
            )
        ),
        "professional_boundary": {
            "definitive": False,
            "message": (
                "Mapped wetlands screening is not a definitive wetlands boundary or "
                "regulatory determination and requires further verification before "
                "professional or regulatory reliance."
            ),
        },
    }


@router.post("/flood")
def screen_flood(payload: EnvironmentalScreeningRequest) -> dict:
    return {
        "kind": "flood",
        "screening": (
            screen_njdep_fema_flood_parcel_geometry(
                parcel_geometry=payload.parcel_geometry,
            )
            if isinstance(payload.parcel_geometry, dict) and payload.parcel_geometry
            else screen_njdep_fema_flood_point(
                longitude=payload.longitude,
                latitude=payload.latitude,
            )
        ),
        "professional_boundary": {
            "definitive": False,
            "message": (
                "Mapped flood screening is an indicator only. It does not calculate "
                "actual flood risk or establish NJDEP regulatory jurisdiction or "
                "Flood Hazard Area rule applicability; further verification is required."
            ),
        },
    }
