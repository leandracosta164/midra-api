from app.api.property_records import (
    _delivery_dynamic_intelligence_from_analysis,
    _delivery_sources_from_analysis,
)
from app.services.property_delivery_orchestration import build_property_delivery_bundle
from app.services.property_report_manifest import build_report_manifest


def _dynamic():
    return {
        "status":"DYNAMIC_ANALYSIS_COMPLETE",
        "dynamic_promotable":False,
        "zoning":{
            "candidate":{"status":"ZONING_CANDIDATE_RESOLVED","record":{
                "municipality":"Example City","block":"1","lot":"2",
                "zoning_district":"R-1","evidence_type":"ARCGIS_SPATIAL_INTERSECTION",
                "source":{"source_url":"https://example.gov/zoning","label":"Municipal zoning GIS"},
            }},
            "promotion":{"status":"VERIFY","promotable":False,"reason":"SOURCE_AUTHORITY_NOT_CONFIRMED"},
        },
        "project_rule_candidate":{
            "status":"PROJECT_RULES_CANDIDATE","municipality":"Example City",
            "zoning_district":"R-1","project_goal":"pool",
            "requirements":[{"requirement":"pool rule evidence"}],
            "source":{"source_url":"https://example.gov/code","label":"Municipal code"},
            "authoritative":False,"legal_control_confirmed":False,
        },
        "project_applicability":{"status":"VERIFY","promotable":False,"reason":"DYNAMIC_ZONING_NOT_PROMOTABLE"},
        "approval_pathway":{"status":"VERIFY","promotable":False,"reason":"DYNAMIC_ZONING_NOT_PROMOTABLE"},
        "professional_boundary":{"definitive":False},
    }


def test_dynamic_delivery_adapter_preserves_candidate_state():
    result=_delivery_dynamic_intelligence_from_analysis({"dynamic_intelligence":_dynamic()})
    assert result["dynamic_promotable"] is False
    assert result["zoning"]["promotion"]["reason"]=="SOURCE_AUTHORITY_NOT_CONFIRMED"
    assert result["project_rule_candidate"]["requirements"][0]["requirement"]=="pool rule evidence"
    assert result["professional_boundary"]["definitive"] is False


def test_delivery_sources_include_dynamic_sources_without_promoting():
    rows=_delivery_sources_from_analysis({"dynamic_intelligence":_dynamic()})
    urls={row.get("source_url") for row in rows}
    assert "https://example.gov/zoning" in urls
    assert "https://example.gov/code" in urls
    assert all(row.get("dynamic_evidence") is True for row in rows)
    assert all(row.get("candidate_only") is True for row in rows)


def test_delivery_bundle_and_report_preserve_dynamic_evidence_separately():
    dynamic=_delivery_dynamic_intelligence_from_analysis({"dynamic_intelligence":_dynamic()})
    bundle=build_property_delivery_bundle(
        analysis_id="a1",
        property_record={"municipality":"Example City","block":"1","lot":"2"},
        project_goal="pool",
        sources=[],
        dynamic_intelligence_evidence=dynamic,
        report_profile="complete",
    )
    assert bundle["master_evidence_package"]["dynamic_intelligence_evidence"]["dynamic_promotable"] is False
    assert bundle["workspace"]["dynamic_intelligence_evidence"]["zoning"]["promotion"]["status"]=="VERIFY"
    report=bundle["customer_report"]
    assert report["sections"]["dynamic_intelligence"] is True
    assert report["sections"]["dynamic_source_index"] is True


def test_preliminary_report_keeps_dynamic_intelligence_without_complete_source_index():
    report=build_report_manifest(
        report_profile="preliminary",
        evidence_package={"dynamic_intelligence_evidence":_dynamic()},
    )
    assert report["sections"]["dynamic_intelligence"] is True
    assert report["sections"]["dynamic_source_index"] is False
