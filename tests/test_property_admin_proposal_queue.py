from pathlib import Path
import re

def test_admin_proposal_queue_route_is_authenticated_and_static():
    text=Path("app/api/property_records.py").read_text(encoding="utf-8")
    static=text.index('@router.get("/admin/proposal-requests"')
    dynamic=text.index('@router.get("/{property_record_id}"')
    assert static < dynamic
    m=re.search(r"def\s+list_admin_engineering_proposal_requests\s*\((.*?)\)\s*:",text,re.S)
    assert m and "Depends(require_property_user)" in m.group(0)

def test_admin_proposal_queue_repository_is_bounded():
    text=Path("app/repositories/property_engineering_proposal_request.py").read_text(encoding="utf-8")
    assert "def list_all(self, limit: int = 100)" in text
    assert ".limit(safe)" in text
    assert "min(int(limit),250)" in text
