from types import SimpleNamespace
from app.api.property_records import _delivery_sources_from_analysis
from app.services.property_delivery_orchestration import build_property_delivery_bundle

def test_delivery_source_adapter_preserves_resolved_map_evidence_only():
    analysis={"property_maps":{"municipality":"Howell","block":"1","lot":"2",
      "zoning_map":{"status":"RESOLVED","source_url":"https://example.gov/zoning.pdf","official_source_verified":True},
      "tax_map":{"status":"VERIFY","reason":"NO_EXPLICIT_TAX_MAP_SOURCE"}}}
    sources=_delivery_sources_from_analysis(analysis)
    assert len(sources)==1
    assert sources[0]["source_role"]=="zoning_map"
    assert sources[0]["authoritative"] is True

def test_delivery_source_adapter_never_invents_missing_urls():
    assert _delivery_sources_from_analysis({"property_maps":{"zoning_map":{"status":"VERIFY"},"tax_map":{}}})==[]

def test_existing_delivery_service_keeps_preliminary_and_complete_evidence_separate():
    source={"label":"Official Zoning Map","source_url":"https://example.gov/zoning.pdf","source_role":"zoning_map","authoritative":True}
    prelim=build_property_delivery_bundle(analysis_id="a1",property_record={"municipality":"Howell","block":"1","lot":"2"},project_goal="pool",sources=[source],report_profile="preliminary")
    complete=build_property_delivery_bundle(analysis_id="a1",property_record={"municipality":"Howell","block":"1","lot":"2"},project_goal="pool",sources=[source],report_profile="complete")
    assert len(prelim["master_evidence_package"]["artifacts"])==1
    assert prelim["customer_report"]["artifact_ids"]==[]
    assert len(complete["customer_report"]["artifact_ids"])==1
    assert prelim["engineering_proposal_request"]["created"] is False
