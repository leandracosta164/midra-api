from types import SimpleNamespace

from app.services.arcgis_spatial_zoning_provider import query_arcgis_zoning_by_geometry
from app.services.dynamic_zoning_analysis import build_dynamic_zoning_evidence
from app.services.zoning_spatial_bridge import resolve_dynamic_spatial_zoning_candidate


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


G1 = {
    "rings": [[[-74.30, 40.20], [-74.29, 40.20], [-74.29, 40.21], [-74.30, 40.20]]],
    "spatialReference": {"wkid": 4326},
}
G2 = {
    "rings": [[[-74.29, 40.20], [-74.28, 40.20], [-74.28, 40.21], [-74.29, 40.20]]],
    "spatialReference": {"wkid": 4326},
}


def _db(*rows):
    class Scalars:
        def all(self):
            return list(rows)

    class DB:
        def scalars(self, _statement):
            return Scalars()

    return DB()


def test_provider_requests_and_preserves_all_same_district_geometry(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs["data"])
        return FakeResponse({
            "features": [
                {"attributes": {"Zone_code": "R-60"}, "geometry": G1},
                {"attributes": {"Zone_code": "R-60"}, "geometry": G2},
            ]
        })

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry=G1,
        municipality="Perth Amboy City",
    )

    assert captured["returnGeometry"] == "true"
    assert captured["outSR"] == "4326"
    assert captured["geometryPrecision"] == "6"
    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert result["district"] == "R-60"
    assert result["mapped_geometries"] == [G1, G2]
    assert result["geometry_role"] == "ZONING_CANDIDATE_GIS_GEOMETRY"
    assert result["geometry_definitive"] is False
    assert result["source"]["authoritative"] is False


def test_provider_does_not_invent_geometry_when_arcgis_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        lambda *args, **kwargs: FakeResponse({
            "features": [{"attributes": {"Zone_code": "R-60"}}]
        }),
    )
    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry=G1,
    )
    assert result["mapped_geometries"] == []
    assert result["geometry_role"] is None
    assert result["geometry_definitive"] is False


def test_dynamic_evidence_preserves_geometry_without_promoting_candidate():
    candidate = {
        "status": "ZONING_CANDIDATE_RESOLVED",
        "record": {
            "municipality": "Perth Amboy City",
            "block": "55",
            "lot": "1",
            "zoning_district": "R-60",
            "evidence_type": "ARCGIS_SPATIAL_INTERSECTION",
            "mapped_geometries": [G1],
            "geometry_role": "ZONING_CANDIDATE_GIS_GEOMETRY",
            "geometry_definitive": False,
            "source": {"authoritative": False, "legal_control_confirmed": False},
        },
    }
    promotion = {
        "status": "VERIFY",
        "promotable": False,
        "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED",
    }
    evidence = build_dynamic_zoning_evidence(candidate, promotion)
    assert evidence["mapped_geometries"] == [G1]
    assert evidence["geometry_role"] == "ZONING_CANDIDATE_GIS_GEOMETRY"
    assert evidence["geometry_definitive"] is False
    assert evidence["promotable"] is False
    assert evidence["status"] == "VERIFY"


def test_bridge_preserves_geometry_and_catalog_authority_independently():
    source = SimpleNamespace(
        id=2,
        municipality="Perth Amboy City",
        label="Verified zoning map",
        source_url="https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
        source_role="zoning_map",
        authority_tier="explicitly_verified",
        evidence_status="LEGAL_CONTROL_CONFIRMED",
        authoritative=True,
        legal_control_confirmed=True,
        active=True,
        current_content_hash="verified",
        current_status="RETRIEVED",
    )

    def metadata(item_id):
        if item_id == "09bd902a48ef45348d2d59283c89673c":
            return {
                "status": "ARCGIS_METADATA_RETRIEVED",
                "data": {"values": {"webmap": "676f6d399a6e4c53913d0b1dde072cd7"}},
            }
        return {"status": "ARCGIS_METADATA_RETRIEVED", "data": {}}

    def discover(_data):
        return {
            "status": "WEBMAP_SERVICES_DISCOVERED",
            "layers": [{
                "url": "https://services.example.gov/arcgis/rest/services/Zoning/FeatureServer/0",
                "title": "Zoning",
                "district_field": "Zone_code",
            }],
        }

    def spatial_query(**kwargs):
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "district": "R-60",
            "attributes": {"Zone_code": "R-60"},
            "mapped_geometries": [G1],
            "geometry_role": "ZONING_CANDIDATE_GIS_GEOMETRY",
            "geometry_definitive": False,
            "source": {
                "url": kwargs["service_url"],
                "district_field": "Zone_code",
                "authoritative": False,
                "legal_control_confirmed": False,
            },
        }

    result = resolve_dynamic_spatial_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry=G1,
        db=_db(source),
        metadata_retriever=metadata,
        webmap_discoverer=discover,
        spatial_query=spatial_query,
    )

    record = result["record"]
    assert record["mapped_geometries"] == [G1]
    assert record["geometry_role"] == "ZONING_CANDIDATE_GIS_GEOMETRY"
    assert record["geometry_definitive"] is False
    assert record["source"]["authoritative"] is True
    assert record["source"]["legal_control_confirmed"] is True
