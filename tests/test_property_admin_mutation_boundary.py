from pathlib import Path
import re

def test_admin_mutations_are_guarded_and_public_intake_stays_public():
    text=Path("app/api/property_records.py").read_text(encoding="utf-8")
    for fn in ("link_property_to_engineering_job","unlink_property_from_engineering_job","transition_engineering_proposal_request_status"):
        m=re.search(rf"def\s+{fn}\s*\((.*?)\)\s*:",text,re.S)
        assert m and "Depends(require_property_user)" in m.group(0)
    m=re.search(r"def\s+request_engineering_proposal\s*\((.*?)\)\s*:",text,re.S)
    assert m and "Depends(require_property_user)" not in m.group(0)
