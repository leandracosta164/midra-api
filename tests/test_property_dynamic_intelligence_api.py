from app.api import property_dynamic_intelligence as api


def test_dynamic_api_refuses_missing_geometry_before_orchestration(monkeypatch):
    called={"value":False}
    def fake_analysis(**kwargs):
        called["value"]=True
        return {}
    monkeypatch.setattr(api,"analyze_dynamic_property",fake_analysis)
    payload=api.DynamicPropertyIntelligenceRequest(
        municipality="Perth Amboy City",
        block="55",
        lot="14",
        parcel_geometry={},
        project_goal="pool",
    )
    result=api.dynamic_property_intelligence(payload,db=object())
    assert result["status"]=="VERIFY"
    assert result["reason"]=="PARCEL_GEOMETRY_OR_IDENTITY_MISSING"
    assert called["value"] is False


def test_dynamic_api_preserves_promotion_guard(monkeypatch):
    monkeypatch.setattr(
        api,
        "analyze_dynamic_property",
        lambda **kwargs:{
            "status":"DYNAMIC_ANALYSIS_COMPLETE",
            "dynamic_promotable":False,
            "zoning":{
                "candidate":{"record":{"zoning_district":"R-60"}},
                "promotion":{"status":"VERIFY","promotable":False,"reason":"SOURCE_AUTHORITY_NOT_CONFIRMED"},
            },
            "project_applicability":{"status":"VERIFY","reason":"DYNAMIC_ZONING_NOT_PROMOTABLE"},
            "approval_pathway":{"status":"VERIFY","reason":"DYNAMIC_ZONING_NOT_PROMOTABLE"},
            "project_rule_candidate":None,
        },
    )
    payload=api.DynamicPropertyIntelligenceRequest(
        municipality="Perth Amboy City",
        block="55",
        lot="14",
        parcel_geometry={"rings":[[[-74.3,40.5],[-74.2,40.5],[-74.2,40.6],[-74.3,40.5]]]},
        project_goal="pool",
    )
    result=api.dynamic_property_intelligence(payload,db=object())
    assert result["dynamic_promotable"] is False
    assert result["zoning"]["promotion"]["reason"]=="SOURCE_AUTHORITY_NOT_CONFIRMED"
    assert result["professional_boundary"]["definitive"] is False


def test_dynamic_api_degrades_to_verify_on_orchestration_error(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("offline")
    monkeypatch.setattr(api,"analyze_dynamic_property",fail)
    payload=api.DynamicPropertyIntelligenceRequest(
        municipality="Perth Amboy City",
        block="55",
        lot="14",
        parcel_geometry={"rings":[[[-74.3,40.5],[-74.2,40.5],[-74.2,40.6],[-74.3,40.5]]]},
        project_goal="pool",
    )
    result=api.dynamic_property_intelligence(payload,db=object())
    assert result["status"]=="VERIFY"
    assert result["reason"]=="DYNAMIC_INTELLIGENCE_UNAVAILABLE"
