from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import property_zoning_candidate as module


PARCEL = {
    "rings": [[[-74.30, 40.20], [-74.29, 40.20], [-74.29, 40.21], [-74.30, 40.20]]],
    "spatialReference": {"wkid": 4326},
}
ZONE = {
    "rings": [[[-74.31, 40.19], [-74.28, 40.19], [-74.28, 40.22], [-74.31, 40.19]]],
    "spatialReference": {"wkid": 4326},
}


def app_client():
    app = FastAPI()
    app.include_router(module.router)
    app.dependency_overrides[module._get_db] = lambda: object()
    return TestClient(app)


def test_candidate_geometry_endpoint_exposes_preserved_geometry_without_promotion(monkeypatch):
    def resolve(**kwargs):
        assert kwargs["municipality"] == "Example City"
        assert kwargs["block"] == "10"
        assert kwargs["lot"] == "2"
        assert kwargs["geometry"] == PARCEL
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "municipality": "Example City",
                "block": "10",
                "lot": "2",
                "zoning_district": "R-60",
                "mapped_geometries": [ZONE],
                "geometry_role": "ZONING_CANDIDATE_GIS_GEOMETRY",
                "geometry_definitive": False,
                "source": {
                    "authoritative": False,
                    "legal_control_confirmed": False,
                },
            },
        }

    monkeypatch.setattr(module, "resolve_dynamic_spatial_zoning_candidate", resolve)

    response = app_client().post(
        "/property/zoning-candidate/geometry",
        json={
            "municipality": "Example City",
            "block": "10",
            "lot": "2",
            "parcel_geometry": PARCEL,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANDIDATE_GEOMETRY_AVAILABLE"
    assert data["candidate_only"] is True
    assert data["candidate"]["record"]["mapped_geometries"] == [ZONE]
    assert data["candidate"]["record"]["geometry_definitive"] is False
    assert data["professional_boundary"]["definitive"] is False
    assert "does not establish authoritative zoning" in data["professional_boundary"]["message"]


def test_candidate_geometry_endpoint_refuses_missing_parcel_geometry(monkeypatch):
    def should_not_run(**kwargs):
        raise AssertionError("resolver must not run without parcel geometry")

    monkeypatch.setattr(module, "resolve_dynamic_spatial_zoning_candidate", should_not_run)

    response = app_client().post(
        "/property/zoning-candidate/geometry",
        json={
            "municipality": "Example City",
            "block": "10",
            "lot": "2",
            "parcel_geometry": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VERIFY"
    assert data["reason"] == "PARCEL_GEOMETRY_NOT_RESOLVED"
    assert data["candidate"] is None
    assert data["professional_boundary"]["definitive"] is False


def test_candidate_without_geometry_remains_verify(monkeypatch):
    monkeypatch.setattr(
        module,
        "resolve_dynamic_spatial_zoning_candidate",
        lambda **kwargs: {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "record": {
                "zoning_district": "R-60",
                "mapped_geometries": [],
                "geometry_definitive": False,
                "source": {"authoritative": False},
            },
        },
    )

    response = app_client().post(
        "/property/zoning-candidate/geometry",
        json={
            "municipality": "Example City",
            "block": "10",
            "lot": "2",
            "parcel_geometry": PARCEL,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VERIFY"
    assert data["candidate_only"] is True
