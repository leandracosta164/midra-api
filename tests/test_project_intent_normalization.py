from app.services.project_intent_normalization import interpret_project_intent, project_intent_search_terms
from app.services.dynamic_project_rule_discovery import discover_dynamic_project_rule_candidate
from app.services.dynamic_approval_pathway_discovery import extract_dynamic_approval_pathway_candidate
from app.services.dynamic_property_analysis import analyze_dynamic_property


def _source(content):
    return {"source_url":"https://example.gov/code","label":"Municipal code","content":content,"authoritative":False,"legal_control_confirmed":False}


def test_common_custom_intents_are_interpreted_without_regulatory_claims():
    mixed=interpret_project_intent("I want a mixed-use building with apartments and retail")
    assert mixed["status"]=="PROJECT_INTENT_INTERPRETED"
    assert mixed["primary_intent"]=="mixed_use"
    assert "multifamily" in mixed["intent_types"]
    assert "retail" in mixed["intent_types"]
    assert "mixed use" in mixed["search_terms"]
    assert mixed["interpretation_basis"]=="EXPLICIT_PROJECT_LANGUAGE"


def test_warehouse_and_solar_get_useful_search_terms():
    assert "warehouse" in project_intent_search_terms("warehouse redevelopment")
    assert "solar array" in project_intent_search_terms("ground-mounted solar array")


def test_unknown_custom_text_remains_custom_but_searchable():
    result=interpret_project_intent("microbrewery tasting room")
    assert result["status"]=="CUSTOM_PROJECT_INTENT"
    assert result["primary_intent"]=="custom"
    assert "microbrewery tasting room" in result["search_terms"]


def test_general_research_does_not_invent_project_terms():
    result=interpret_project_intent("other")
    assert result["status"]=="GENERAL_PROPERTY_RESEARCH"
    assert result["search_terms"]==[]


def test_dynamic_rule_discovery_uses_interpreted_mixed_use_terms():
    result=discover_dynamic_project_rule_candidate(
        municipality="Example City",zoning_district="MU-1",project_goal="mixed-use building",
        source_documents=[_source("MU-1 Zone. Permitted uses include mixed use development with residential and retail uses.")],
    )
    assert result["status"]=="PROJECT_RULE_EVIDENCE_DISCOVERED"


def test_approval_discovery_uses_interpreted_solar_terms():
    result=extract_dynamic_approval_pathway_candidate(
        municipality="Example City",zoning_district="I-1",project_goal="ground-mounted solar array",
        source_document=_source("I-1 district. A solar energy system requires site plan approval by the Planning Board."),
    )
    assert result["status"]=="APPROVAL_PATHWAY_CANDIDATE"
    assert result["primary_pathway"]=="SITE_PLAN_APPROVAL"


def test_dynamic_analysis_preserves_project_intent_summary():
    result=analyze_dynamic_property(
        municipality="Example City",block="1",lot="2",geometry={"rings":[]},project_goal="warehouse redevelopment",db=object(),
        zoning_analysis=lambda **_: {"status":"VERIFY","candidate":{"record":{"zoning_district":"I-1"}},"promotion":{"status":"VERIFY","promotable":False}},
        project_rule_discoverer=lambda **_: {"status":"VERIFY"},
        approval_pathway_discoverer=lambda **_: None,
    )
    assert result["project_intent"]["primary_intent"]=="warehouse"
    assert result["project_applicability"]["reason"]=="DYNAMIC_ZONING_NOT_PROMOTABLE"
