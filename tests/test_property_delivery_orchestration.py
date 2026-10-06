import pytest

from app.services.property_delivery_orchestration import (
    build_property_delivery_bundle,
    request_engineering_proposal,
)


def _property():
    return {"address": "48 Victor Avenue", "municipality": "West Long Branch", "block": "55", "lot": "14"}


def _sources():
    return [
        {"label": "Official Zoning Map", "source_url": "https://example.gov/zoning.pdf", "source_role": "zoning_map", "municipal_official_link_verified": True, "content_hash": "z1"},
        {"label": "Tax Map Sheet 12", "source_url": "https://example.gov/tax12.pdf", "source_role": "tax_map", "municipal_official_link_verified": True, "tax_map_sheet": "12", "content_hash": "t1"},
    ]


def test_preliminary_delivery_retains_complete_master_evidence_without_embedding_map_exhibits():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="new house", sources=_sources(), report_profile="preliminary")
    assert bundle["customer_report_profile"] == "PRELIMINARY"
    assert len(bundle["master_evidence_package"]["artifacts"]) == 2
    assert bundle["customer_report"]["artifact_ids"] == []
    assert bundle["customer_report"]["sections"]["midra_property_map"] is True
    assert bundle["customer_report"]["sections"]["zoning_map_exhibit"] is False
    assert bundle["customer_report"]["sections"]["tax_map_exhibit"] is False


def test_complete_delivery_uses_same_master_evidence_and_includes_verified_map_exhibits():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="new house", sources=_sources(), report_profile="complete")
    assert bundle["customer_report_profile"] == "COMPLETE"
    assert len(bundle["master_evidence_package"]["artifacts"]) == 2
    assert len(bundle["customer_report"]["artifact_ids"]) == 2


def test_workspace_exposes_original_map_view_and_download_independent_of_report_profile():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="new house", sources=_sources(), report_profile="preliminary")
    assert len(bundle["workspace"]["map_artifacts"]) == 2
    assert all(item["view_original"] for item in bundle["workspace"]["map_artifacts"])
    assert all(item["download_original"] for item in bundle["workspace"]["map_artifacts"])


def test_engineering_handoff_is_not_created_merely_by_generating_a_report():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="new house", sources=_sources())
    assert bundle["engineering_proposal_request"]["available"] is True
    assert bundle["engineering_proposal_request"]["created"] is False
    assert bundle["engineering_proposal_request"]["destination_product"] == "MIDRA_ENGINEERING"


def test_explicit_proposal_request_reuses_preliminary_analysis_but_gives_engineering_full_evidence():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="new house", sources=_sources(), report_profile="preliminary", analysis_snapshot={"as_of": "2026-09-18"})
    handoff = request_engineering_proposal(delivery_bundle=bundle, customer={"name": "Jane Smith"})
    assert handoff["source_product"] == "MIDRA_INTELLIGENCE"
    assert handoff["destination_product"] == "MIDRA_ENGINEERING"
    assert handoff["duplicate_property_research_required"] is False
    assert handoff["customer_report_profile"] == "PRELIMINARY"
    assert len(handoff["evidence_package"]["artifacts"]) == 2
    assert handoff["engineering_access"]["zoning_map"] is True
    assert handoff["engineering_access"]["tax_map"] is True
    assert handoff["customer_entitlement_unchanged"] is True
    assert handoff["analysis_snapshot"] == {"as_of": "2026-09-18"}


def test_proposal_request_keeps_agreed_cta_and_no_extra_permission_state():
    bundle = build_property_delivery_bundle(analysis_id="MI-1847", property_record=_property(), project_goal="pool", sources=[])
    assert bundle["engineering_proposal_request"]["cta_copy"]["action"] == "REQUEST AN ENGINEERING PROPOSAL"
    handoff = request_engineering_proposal(delivery_bundle=bundle)
    assert handoff["separate_share_permission_step"] is False


def test_delivery_requires_municipality_and_handoff_requires_intelligence_origin():
    with pytest.raises(ValueError):
        build_property_delivery_bundle(analysis_id="MI-1", property_record={"address": "x"}, project_goal="pool", sources=[])
    with pytest.raises(ValueError):
        request_engineering_proposal(delivery_bundle={"product": "MIDRA_ENGINEERING", "analysis_id": "MI-1"})
