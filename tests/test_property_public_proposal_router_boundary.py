from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def _signature(text,name):
    m=re.search(rf"def\s+{name}\s*\((.*?)\)\s*:",text,re.S)
    assert m, name
    return m.group(0)

def test_public_proposal_intake_and_exact_context_use_public_router():
    main=(ROOT/"app/main.py").read_text(encoding="utf-8")
    api=(ROOT/"app/api/property_records.py").read_text(encoding="utf-8")

    assert "public_router as public_property_records_router" in main
    assert "app.include_router(public_property_records_router)" in main
    assert "app.include_router(property_records_router, dependencies=[Depends(require_property_user)])" in main

    assert '@public_router.post("/{property_record_id}/engineering-proposal-requests"' in api
    assert '"/{property_record_id}/engineering-proposal-requests/{proposal_request_id}/context"' in api
    assert "Depends(require_property_user)" not in _signature(api,"request_engineering_proposal")
    assert "Depends(require_property_user)" not in _signature(api,"get_engineering_proposal_request_context")

def test_private_proposal_enumeration_and_admin_mutations_remain_authenticated():
    api=(ROOT/"app/api/property_records.py").read_text(encoding="utf-8")
    for fn in (
        "list_engineering_proposal_requests",
        "list_admin_engineering_proposal_requests",
        "list_property_engineering_links",
        "link_property_to_engineering_job",
        "unlink_property_from_engineering_job",
        "transition_engineering_proposal_request_status",
    ):
        assert "Depends(require_property_user)" in _signature(api,fn), fn
