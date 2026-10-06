from app.services.njdep_environmental_screening import (
    screen_njdep_fema_flood_point,
    screen_njdep_wetlands_parcel_geometry,
    screen_njdep_wetlands_point,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _assert_conservative_source(source):
    assert source["authoritative_agency_source"] is True
    assert source["current_status"] == "VERIFY_CURRENTNESS"
    assert isinstance(source["last_checked_at"], str) and source["last_checked_at"].endswith("Z")
    assert source["retrieved_at"] == source["last_checked_at"]
    assert "does not infer" in source["currentness_note"] or "did not independently establish" in source["currentness_note"]
    assert source["current_status"] != "CURRENT"


def test_wetlands_point_records_retrieval_time_without_currentness_promotion():
    result = screen_njdep_wetlands_point(
        longitude=-74.3,
        latitude=40.2,
        post=lambda *a, **k: Response({"features": []}),
    )
    _assert_conservative_source(result["source"])
    assert result["screening_result"] == "NO_MAPPED_INTERSECTION_RETURNED"


def test_flood_point_records_retrieval_time_without_currentness_promotion():
    result = screen_njdep_fema_flood_point(
        longitude=-74.3,
        latitude=40.2,
        post=lambda *a, **k: Response({"features": []}),
    )
    _assert_conservative_source(result["source"])
    assert result["actual_flood_risk_calculated"] is False


def test_wetlands_parcel_records_same_provenance_contract():
    parcel = {
        "rings": [[[-74.31, 40.20], [-74.30, 40.20], [-74.30, 40.21], [-74.31, 40.20]]]
    }
    result = screen_njdep_wetlands_parcel_geometry(
        parcel_geometry=parcel,
        post=lambda *a, **k: Response({"features": []}),
    )
    _assert_conservative_source(result["source"])
    assert result["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
