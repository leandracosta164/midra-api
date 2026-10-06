from types import SimpleNamespace

from app.services.zoning_source_selector import select_zoning_source_candidates


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, statement):
        return _ScalarResult(self.rows)


def _row(municipality, label="Zoning Map Links", source_role="zoning_map", active=True):
    return SimpleNamespace(
        id=1,
        municipality=municipality,
        label=label,
        source_url="https://example.test/zoning",
        source_role=source_role,
        authority_tier="external_or_unknown_domain",
        evidence_status="DISCOVERED_CANDIDATE",
        authoritative=False,
        legal_control_confirmed=False,
        active=active,
        current_content_hash=None,
        current_status="UNCHANGED",
    )


def test_selector_matches_case_and_city_suffix():
    rows = [_row("Perth Amboy City")]
    result = select_zoning_source_candidates(
        municipality="PERTH AMBOY CITY",
        db=_FakeDB(rows),
    )
    assert len(result) == 1
    assert result[0]["municipality"] == "Perth Amboy City"


def test_selector_matches_different_standard_suffix():
    rows = [_row("Sample Borough")]
    result = select_zoning_source_candidates(
        municipality="sample",
        db=_FakeDB(rows),
    )
    assert len(result) == 1


def test_selector_does_not_match_different_municipality():
    rows = [_row("Perth Amboy City"), _row("Newark City")]
    result = select_zoning_source_candidates(
        municipality="Marlboro Township",
        db=_FakeDB(rows),
    )
    assert result == []
