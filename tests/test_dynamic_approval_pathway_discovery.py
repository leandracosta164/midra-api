from app.services.dynamic_approval_pathway_discovery import (
    discover_dynamic_approval_pathway_candidate,
    extract_dynamic_approval_pathway_candidate,
)
from app.services.dynamic_property_analysis import analyze_dynamic_property


def _doc(*, authoritative=False, legal=False):
    return {
        "source_url":"https://example.gov/code",
        "label":"Municipal Land Use Code",
        "source_role":"zoning_ordinance",
        "authoritative":authoritative,
        "legal_control_confirmed":legal,
        "content":(
            "R-1 residential district. A swimming pool requires site plan approval "
            "by the Planning Board before construction."
        ),
    }


def test_discovers_explicit_pathway_and_reviewing_body_without_promoting_source():
    result=extract_dynamic_approval_pathway_candidate(
        municipality="Example City",
        zoning_district="R-1",
        project_goal="pool",
        source_document=_doc(),
    )
    assert result["status"]=="APPROVAL_PATHWAY_CANDIDATE"
    assert result["primary_pathway"]=="SITE_PLAN_APPROVAL"
    assert result["reviewing_bodies"]==["PLANNING_BOARD"]
    assert result["authoritative"] is False
    assert result["legal_control_confirmed"] is False


def test_no_explicit_pathway_returns_verify():
    result=extract_dynamic_approval_pathway_candidate(
        municipality="Example City",
        zoning_district="R-1",
        project_goal="pool",
        source_document={**_doc(), "content":"R-1 residential district permits swimming pools."},
    )
    assert result["status"]=="VERIFY"
    assert result["reason"]=="APPROVAL_PATHWAY_NOT_EXPLICIT"


def test_discoverer_returns_none_when_no_source_supports_pathway():
    assert discover_dynamic_approval_pathway_candidate(
        municipality="Example City",
        zoning_district="R-1",
        project_goal="pool",
        source_documents=[{**_doc(), "content":"Swimming pools are accessory uses."}],
    ) is None


def test_dynamic_property_analysis_promotes_only_after_existing_zoning_and_legal_guards():
    project_candidate={
        "status":"PROJECT_RULES_CANDIDATE",
        "municipality":"Example City",
        "zoning_district":"R-1",
        "project_goal":"pool",
        "requirements":[{"requirement":"Pool review","registry_applicability":"applicable"}],
        "authoritative":True,
        "legal_control_confirmed":True,
        "source":{"source_url":"https://example.gov/code","authoritative":True},
    }
    approval_candidate=extract_dynamic_approval_pathway_candidate(
        municipality="Example City",
        zoning_district="R-1",
        project_goal="pool",
        source_document=_doc(authoritative=True, legal=True),
    )

    result=analyze_dynamic_property(
        municipality="Example City",
        block="1",
        lot="2",
        geometry={"rings":[]},
        project_goal="pool",
        db=object(),
        zoning_analysis=lambda **_: {
            "status":"ZONING_RESOLVED",
            "candidate":{"record":{"zoning_district":"R-1"}},
            "promotion":{"status":"ZONING_RESOLVED","promotable":True},
        },
        project_rule_candidate=project_candidate,
        approval_pathway_discoverer=lambda **_: approval_candidate,
    )

    assert result["approval_pathway_candidate"]["primary_pathway"]=="SITE_PLAN_APPROVAL"
    assert result["approval_pathway"]["status"]=="AVAILABLE"
    assert result["approval_pathway"]["promotable"] is True


def test_dynamic_property_analysis_blocks_approval_when_zoning_not_promotable():
    candidate=extract_dynamic_approval_pathway_candidate(
        municipality="Example City",
        zoning_district="R-1",
        project_goal="pool",
        source_document=_doc(authoritative=True, legal=True),
    )
    result=analyze_dynamic_property(
        municipality="Example City",
        block="1",
        lot="2",
        geometry={"rings":[]},
        project_goal="pool",
        db=object(),
        zoning_analysis=lambda **_: {
            "status":"VERIFY",
            "candidate":{"record":{"zoning_district":"R-1"}},
            "promotion":{"status":"VERIFY","promotable":False},
        },
        approval_pathway_discoverer=lambda **_: candidate,
    )
    assert result["approval_pathway"]["reason"]=="DYNAMIC_ZONING_NOT_PROMOTABLE"
    assert result["approval_pathway"]["promotable"] is False
