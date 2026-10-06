from pathlib import Path
import re

def _api():
    return Path("app/api/property_records.py").read_text(encoding="utf-8")

def _signature(text,name):
    m=re.search(rf"def\s+{name}\s*\((.*?)\)\s*:",text,re.S)
    assert m
    return m.group(0)

def test_all_property_engineering_link_reads_and_mutations_require_property_admin():
    text=_api()
    for name in (
        "list_property_engineering_links",
        "link_property_to_engineering_job",
        "unlink_property_from_engineering_job",
    ):
        assert "Depends(require_property_user)" in _signature(text,name)
