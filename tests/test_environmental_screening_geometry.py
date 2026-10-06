from app.services.njdep_environmental_screening import (
    screen_njdep_wetlands_point,
    screen_njdep_fema_flood_point,
)

class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload

POLYGON={"rings":[[[-74.30,40.20],[-74.29,40.20],[-74.29,40.21],[-74.30,40.20]]],"spatialReference":{"wkid":4326}}

def test_wetlands_preserves_returned_polygon_as_nondefinitive_screening_geometry():
    seen={}
    def post(url, **kwargs):
        seen.update(kwargs["data"])
        return Response({"features":[{"attributes":{"OBJECTID":1,"LABEL12":"DECIDUOUS WOODED WETLANDS","TYPE12":"WETLANDS","ACRES":2.4},"geometry":POLYGON}]})
    result=screen_njdep_wetlands_point(longitude=-74.3,latitude=40.2,post=post)
    assert seen["returnGeometry"]=="true"
    assert seen["outSR"]=="4326"
    item=result["evidence"][0]
    assert item["mapped_geometry"]==POLYGON
    assert item["geometry_role"]=="AUTHORITATIVE_GIS_SCREENING_GEOMETRY"
    assert item["geometry_definitive"] is False
    assert result["regulatory_determination"] is False

def test_flood_preserves_returned_polygon_without_promoting_risk_or_jurisdiction():
    seen={}
    def post(url, **kwargs):
        seen.update(kwargs["data"])
        return Response({"features":[{"attributes":{"OBJECTID":7,"FLD_ZONE":"AE","ZONE_SUBTY":None},"geometry":POLYGON}]})
    result=screen_njdep_fema_flood_point(longitude=-74.3,latitude=40.2,post=post)
    assert seen["returnGeometry"]=="true"
    assert seen["outSR"]=="4326"
    item=result["evidence"][0]
    assert item["mapped_geometry"]==POLYGON
    assert item["geometry_definitive"] is False
    assert result["actual_flood_risk_calculated"] is False
    assert result["regulatory_determination"] is False

def test_missing_geometry_keeps_screening_result_but_does_not_invent_boundary():
    result=screen_njdep_wetlands_point(
        longitude=-74.3,latitude=40.2,
        post=lambda *a,**k:Response({"features":[{"attributes":{"OBJECTID":2,"LABEL12":"WETLAND","TYPE12":"WETLAND","ACRES":1.0}}]})
    )
    assert result["mapped_intersection"] is True
    assert result["evidence"][0]["mapped_geometry"] is None
    assert result["evidence"][0]["geometry_definitive"] is False
