from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import (
    build_workplace_attention_queue,
    build_workplace_verification_attention,
)


def test_property_verify_context_enters_unified_attention_queue():
    run=SimpleNamespace(
        property_record_id="p1",
        analysis_run_id="a1",
        created_at=None,
        analysis={"verification_items":["Verify controlling zoning source."]},
    )
    prop=SimpleNamespace(
        display_address="1 Main St",
        search_query="1 Main St",
        municipality="Howell",
        county="Monmouth",
    )
    verification=build_workplace_verification_attention([run],{"p1":prop})
    assert len(verification)==1
    assert verification[0]["kind"]=="PROPERTY_VERIFY"
    assert verification[0]["href"]=="evidence.html?property_record_id=p1"
    assert verification[0]["next_action"]=="REVIEW_PROPERTY_EVIDENCE"
    queue=build_workplace_attention_queue([],[],verification)
    assert queue[0]["kind"]=="PROPERTY_VERIFY"


def test_property_without_verify_context_is_not_added():
    run=SimpleNamespace(property_record_id="p1",analysis_run_id="a1",created_at=None,analysis={})
    assert build_workplace_verification_attention([run],{})==[]
