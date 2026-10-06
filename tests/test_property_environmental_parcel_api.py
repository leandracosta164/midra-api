from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import property_environmental_screening as module


PARCEL = {
    "rings": [[
        [-74.30, 40.20],
        [-74.29, 40.20],
        [-74.29, 40.21],
        [-74.30, 40.20],
    ]],
    "spatialReference": {"wkid": 4326},
}


def app_client():
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def test_wetlands_endpoint_prefers_parcel_geometry_when_supplied(monkeypatch):
    calls = {"parcel": 0, "point": 0}

    def parcel(**kwargs):
        calls["parcel"] += 1
        assert kwargs["parcel_geometry"] == PARCEL
        return {
            "status": "SCREENING_COMPLETE",
            "screening_basis": "PARCEL_GEOMETRY_INTERSECTION",
            "mapped_intersection": True,
            "regulatory_determination": False,
        }

    def point(**kwargs):
        calls["point"] += 1
        raise AssertionError("point fallback should not run")

    monkeypatch.setattr(module, "screen_njdep_wetlands_parcel_geometry", parcel)
    monkeypatch.setattr(module, "screen_njdep_wetlands_point", point)

    response = app_client().post(
        "/property/environmental-screening/wetlands",
        json={"latitude": 40.2, "longitude": -74.3, "parcel_geometry": PARCEL},
    )
    assert response.status_code == 200
    assert response.json()["screening"]["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
    assert calls == {"parcel": 1, "point": 0}


def test_flood_endpoint_keeps_point_fallback_without_parcel_geometry(monkeypatch):
    monkeypatch.setattr(
        module,
        "screen_njdep_fema_flood_point",
        lambda **kwargs: {
            "status": "SCREENING_COMPLETE",
            "mapped_intersection": False,
            "actual_flood_risk_calculated": False,
            "regulatory_determination": False,
        },
    )
    response = app_client().post(
        "/property/environmental-screening/flood",
        json={"latitude": 40.2, "longitude": -74.3},
    )
    assert response.status_code == 200
    assert response.json()["screening"]["mapped_intersection"] is False
