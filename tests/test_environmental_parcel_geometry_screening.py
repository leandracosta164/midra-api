import json

from app.services.njdep_environmental_screening import (
    screen_njdep_wetlands_parcel_geometry,
    screen_njdep_fema_flood_parcel_geometry,
)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


PARCEL = {
    "rings": [[
        [-74.30, 40.20],
        [-74.29, 40.20],
        [-74.29, 40.21],
        [-74.30, 40.20],
    ]],
    "spatialReference": {"wkid": 4326},
}

WETLAND = {
    "rings": [[
        [-74.295, 40.202],
        [-74.292, 40.202],
        [-74.292, 40.205],
        [-74.295, 40.202],
    ]],
    "spatialReference": {"wkid": 4326},
}


def test_wetlands_parcel_query_uses_polygon_intersection_and_preserves_geometry():
    seen = {}

    def post(url, **kwargs):
        seen.update(kwargs["data"])
        return Response({
            "features": [{
                "attributes": {
                    "OBJECTID": 1,
                    "LABEL12": "WETLAND",
                    "TYPE12": "WETLANDS",
                    "ACRES": 1.2,
                },
                "geometry": WETLAND,
            }]
        })

    result = screen_njdep_wetlands_parcel_geometry(
        parcel_geometry=PARCEL,
        post=post,
    )

    assert seen["geometryType"] == "esriGeometryPolygon"
    assert seen["spatialRel"] == "esriSpatialRelIntersects"
    assert json.loads(seen["geometry"])["rings"] == PARCEL["rings"]
    assert result["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
    assert result["mapped_intersection"] is True
    assert result["evidence"][0]["mapped_geometry"] == WETLAND
    assert result["regulatory_determination"] is False
    assert any("not a surveyed or legal parcel boundary" in x for x in result["limitations"])


def test_wetlands_no_parcel_intersection_does_not_establish_absence():
    result = screen_njdep_wetlands_parcel_geometry(
        parcel_geometry=PARCEL,
        post=lambda *a, **k: Response({"features": []}),
    )
    assert result["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
    assert result["mapped_intersection"] is False
    assert result["screening_result"] == "NO_MAPPED_INTERSECTION_RETURNED"
    assert any("does not establish" in x for x in result["limitations"])


def test_flood_parcel_query_is_not_actual_risk_or_jurisdiction():
    result = screen_njdep_fema_flood_parcel_geometry(
        parcel_geometry=PARCEL,
        post=lambda *a, **k: Response({
            "features": [{
                "attributes": {"OBJECTID": 9, "FLD_ZONE": "AE", "ZONE_SUBTY": None},
                "geometry": WETLAND,
            }]
        }),
    )
    assert result["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
    assert result["mapped_intersection"] is True
    assert result["actual_flood_risk_calculated"] is False
    assert result["regulatory_determination"] is False


def test_invalid_parcel_geometry_remains_verify():
    result = screen_njdep_wetlands_parcel_geometry(parcel_geometry={"rings": []})
    assert result["status"] == "VERIFY"
    assert result["mapped_intersection"] is None
    assert result["screening_basis"] == "PARCEL_GEOMETRY_INTERSECTION"
