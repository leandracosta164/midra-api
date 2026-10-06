from app.services.njdep_environmental_screening import screen_njdep_wetlands_point

class Response:
    def __init__(self,payload): self.payload=payload
    def raise_for_status(self): return None
    def json(self): return self.payload

def test_mapped_wetland_is_screening_not_regulatory_determination():
    def post(url,**kwargs):
        assert "mapsdep.nj.gov" in url
        assert kwargs["data"]["inSR"]=="4326"
        return Response({"features":[{"attributes":{"OBJECTID":1,"LABEL12":"DECIDUOUS WOODED WETLANDS","TYPE12":"WETLANDS","ACRES":2.5}}]})
    result=screen_njdep_wetlands_point(longitude=-74.3,latitude=40.2,post=post)
    assert result["status"]=="SCREENING_COMPLETE"
    assert result["mapped_intersection"] is True
    assert result["screening_result"]=="MAPPED_WETLANDS_INTERSECTION"
    assert result["regulatory_determination"] is False
    assert result["source"]["authoritative_agency_source"] is True

def test_no_feature_is_not_promoted_to_no_wetlands():
    result=screen_njdep_wetlands_point(
        longitude=-74.3,latitude=40.2,post=lambda *a,**k:Response({"features":[]})
    )
    assert result["mapped_intersection"] is False
    assert result["screening_result"]=="NO_MAPPED_INTERSECTION_RETURNED"
    assert result["regulatory_determination"] is False
    assert any("does not establish" in x for x in result["limitations"])

def test_missing_coordinates_remain_verify():
    result=screen_njdep_wetlands_point(longitude=None,latitude=None)
    assert result["status"]=="VERIFY"
    assert result["mapped_intersection"] is None
    assert result["regulatory_determination"] is False

def test_zoning_registry_contract_is_defensively_preserved_in_api_source():
    from pathlib import Path
    main=(Path(__file__).resolve().parents[1]/"app"/"main.py").read_text(encoding="utf-8")
    assert 'zoning_intelligence.setdefault(' in main
    assert '"rules_registry"' in main
    assert '"project_rules_available": False' in main
