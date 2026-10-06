from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import property_environmental_screening as module

def app_client():
    app=FastAPI()
    app.include_router(module.router)
    return TestClient(app)

def test_wetlands_endpoint_preserves_screening_boundary(monkeypatch):
    monkeypatch.setattr(module,"screen_njdep_wetlands_point",lambda **kwargs:{
        "status":"SCREENING_COMPLETE",
        "screening_result":"MAPPED_WETLANDS_INTERSECTION",
        "mapped_intersection":True,
        "regulatory_determination":False,
        "source":{"agency":"New Jersey Department of Environmental Protection"},
    })
    r=app_client().post("/property/environmental-screening/wetlands",json={"latitude":40.2,"longitude":-74.3})
    assert r.status_code==200
    data=r.json()
    assert data["screening"]["mapped_intersection"] is True
    assert data["screening"]["regulatory_determination"] is False
    assert data["professional_boundary"]["definitive"] is False
    assert "requires further verification" in data["professional_boundary"]["message"]

def test_wetlands_endpoint_rejects_invalid_coordinates():
    r=app_client().post("/property/environmental-screening/wetlands",json={"latitude":140.2,"longitude":-74.3})
    assert r.status_code==422

def test_flood_endpoint_preserves_indicator_boundary(monkeypatch):
    monkeypatch.setattr(module,"screen_njdep_fema_flood_point",lambda **kwargs:{"status":"SCREENING_COMPLETE","screening_result":"MAPPED_FLOOD_ZONE_INTERSECTION","mapped_intersection":True,"actual_flood_risk_calculated":False,"regulatory_determination":False})
    r=app_client().post("/property/environmental-screening/flood",json={"latitude":40.2,"longitude":-74.3})
    assert r.status_code==200
    d=r.json(); assert d["professional_boundary"]["definitive"] is False
    assert "further verification is required" in d["professional_boundary"]["message"]
