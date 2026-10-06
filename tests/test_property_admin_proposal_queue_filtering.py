from pathlib import Path

def test_existing_list_all_contract_is_preserved_for_historical_verifiers():
    text=Path("app/repositories/property_engineering_proposal_request.py").read_text(encoding="utf-8")
    assert 'def list_all(self, limit: int = 100)' in text

def test_status_filter_has_separate_bounded_repository_method():
    text=Path("app/repositories/property_engineering_proposal_request.py").read_text(encoding="utf-8")
    start=text.index("def list_all_by_status(")
    block=text[start:start+1400]
    assert "request_status==normalized_status" in block
    assert ".limit(safe)" in block
    assert 'return self.list_all(limit=safe)' in block

def test_admin_queue_api_remains_authenticated_and_uses_filtered_method():
    text=Path("app/api/property_records.py").read_text(encoding="utf-8")
    start=text.index("def list_admin_engineering_proposal_requests(")
    block=text[start:start+1800]
    assert "request_status: str | None = None" in block
    assert "Depends(require_property_user)" in block
    assert "list_all_by_status(normalized_status, limit=limit)" in block
