from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.zoning_source_selector import select_zoning_source_candidates


class ScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class DB:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, _statement):
        return ScalarResult(self.rows)


def test_selector_preserves_catalog_currentness_metadata():
    checked = datetime(2026, 9, 28, 20, 30, tzinfo=timezone.utc)
    discovered = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(
        id=1,
        municipality="Example City",
        label="Official Zoning",
        source_url="https://example.gov/zoning",
        retrieval_url="https://example.gov/arcgis/rest/services/zoning",
        source_role="zoning_map",
        authority_tier="municipal_official",
        evidence_status="LEGAL_CONTROL_CONFIRMED",
        authoritative=True,
        legal_control_confirmed=True,
        active=True,
        first_discovered_at=discovered,
        last_checked_at=checked,
        current_content_hash="abc123",
        current_status="UNCHANGED",
        discovery_source="municipal_site",
        source_type="arcgis",
    )

    result = select_zoning_source_candidates(municipality="Example City", db=DB([row]))
    assert len(result) == 1
    source = result[0]
    assert source["retrieval_url"] == row.retrieval_url
    assert source["first_discovered_at"] == discovered.isoformat()
    assert source["last_checked_at"] == checked.isoformat()
    assert source["current_status"] == "UNCHANGED"
    assert source["current_content_hash"] == "abc123"
    assert source["authoritative"] is True
    assert source["legal_control_confirmed"] is True
