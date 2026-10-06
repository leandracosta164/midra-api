from pathlib import Path
import re

def _api():
    return Path("app/api/property_records.py").read_text(encoding="utf-8")

def _signature(text,name):
    m=re.search(rf"def\s+{name}\s*\((.*?)\)\s*:",text,re.S)
    assert m
    return m.group(0)

def test_bulk_proposal_history_is_admin_only_but_public_intake_and_exact_context_remain_public():
    text=_api()
    assert "Depends(require_property_user)" in _signature(text,"list_engineering_proposal_requests")
    assert "Depends(require_property_user)" not in _signature(text,"request_engineering_proposal")
    assert "Depends(require_property_user)" not in _signature(text,"get_engineering_proposal_request_context")
