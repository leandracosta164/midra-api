from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def test_public_proposal_intake_bridge_is_public_and_bounded_to_explicit_handoff():
    api=(ROOT/"app/api/property_records.py").read_text(encoding="utf-8")
    schema=(ROOT/"app/schemas/property_record.py").read_text(encoding="utf-8")
    assert '"/public/proposal-intake"' in api
    assert "PropertyEngineeringProposalPublicIntakeCreate" in schema
    m=re.search(r"def\s+create_public_engineering_proposal_intake\s*\((.*?)\)\s*:",api,re.S)
    assert m
    assert "Depends(require_property_user)" not in m.group(0)
    assert "upsert_from_analysis" in api
    assert "PropertyAnalysisRunRepository(db).append" in api
    assert "PropertyEngineeringProposalRequestRepository(db).create" in api

def test_private_enumeration_and_mutation_boundaries_remain_authenticated():
    api=(ROOT/"app/api/property_records.py").read_text(encoding="utf-8")
    for fn in (
        "list_engineering_proposal_requests",
        "list_admin_engineering_proposal_requests",
        "transition_engineering_proposal_request_status",
        "list_property_engineering_links",
        "link_property_to_engineering_job",
        "unlink_property_from_engineering_job",
    ):
        m=re.search(rf"def\s+{fn}\s*\((.*?)\)\s*:",api,re.S)
        assert m and "Depends(require_property_user)" in m.group(0), fn
