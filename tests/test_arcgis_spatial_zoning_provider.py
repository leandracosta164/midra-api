from app.services.arcgis_spatial_zoning_provider import query_arcgis_zoning_by_geometry


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_spatial_provider_resolves_unique_district(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({
            "features": [{"attributes": {"Zone_code": "R-50"}}]
        })

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={"rings": [[[1, 2], [3, 4], [1, 2]]]},
        municipality="Perth Amboy City",
    )

    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert result["district"] == "R-50"
    assert result["source"]["authoritative"] is False


def test_spatial_provider_rejects_ambiguous_districts(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({
            "features": [
                {"attributes": {"Zone_code": "R-50"}},
                {"attributes": {"Zone_code": "C-1"}},
            ]
        })

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={"rings": [[[1, 2], [3, 4], [1, 2]]]},
    )

    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["reason"] == "AMBIGUOUS_DISTRICT"


def test_spatial_provider_handles_arcgis_errors(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"error": {"code": 400, "message": "bad geometry"}})

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={"rings": []},
    )

    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["reason"] == "ARCGIS_QUERY_ERROR"


def test_spatial_provider_never_marks_result_authoritative(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse({"features": [{"attributes": {"Zone_code": "R-60"}}]})

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={"rings": [[[1, 2], [3, 4], [1, 2]]]},
    )

    assert result["source"]["authoritative"] is False


def test_spatial_provider_passes_geometry_spatial_reference(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"features": [{"attributes": {"Zone_code": "R-60"}}]})

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={
            "rings": [[[1, 2], [3, 4], [1, 2]]],
            "spatialReference": {"wkid": 4326},
        },
    )

    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert captured["data"]["inSR"] == "4326"


def test_spatial_provider_uses_post_with_geometry_payload(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"features": [{"attributes": {"Zone_code": "R-60"}}]})

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={
            "rings": [[[1, 2], [3, 4], [1, 2]]],
            "spatialReference": {"wkid": 4326},
        },
    )

    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert captured["data"]["inSR"] == "4326"
    assert captured["data"]["geometryType"] == "esriGeometryPolygon"


def test_spatial_provider_accepts_explicit_spatial_reference_when_geometry_omits_it(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"features": [{"attributes": {"Zone_code": "R-60"}}]})

    monkeypatch.setattr(
        "app.services.arcgis_spatial_zoning_provider.httpx.post",
        fake_post,
    )

    result = query_arcgis_zoning_by_geometry(
        service_url="https://example.arcgis.com/FeatureServer/0",
        district_field="Zone_code",
        geometry={"rings": [[[1, 2], [3, 4], [1, 2]]]},
        spatial_reference_wkid=4326,
    )

    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert captured["data"]["inSR"] == "4326"
