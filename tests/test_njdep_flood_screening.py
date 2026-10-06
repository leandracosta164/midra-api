from app.services.njdep_environmental_screening import screen_njdep_fema_flood_point
class Response:
    def __init__(self,p): self.p=p
    def raise_for_status(self): return None
    def json(self): return self.p
def test_intersection_is_indicator_only():
    r=screen_njdep_fema_flood_point(longitude=-74.3,latitude=40.2,post=lambda *a,**k:Response({"features":[{"attributes":{"OBJECTID":8,"FLD_ZONE":"AE","ZONE_SUBTY":None}}]}))
    assert r["screening_result"]=="MAPPED_FLOOD_ZONE_INTERSECTION"; assert r["actual_flood_risk_calculated"] is False; assert r["regulatory_determination"] is False
def test_no_intersection_is_not_no_risk():
    r=screen_njdep_fema_flood_point(longitude=-74.3,latitude=40.2,post=lambda *a,**k:Response({"features":[]}))
    assert r["screening_result"]=="NO_MAPPED_INTERSECTION_RETURNED"; assert any("does not establish" in x for x in r["limitations"])
