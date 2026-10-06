from types import SimpleNamespace

from app.services.zoning_evidence_provider import ZoningEvidenceRecord
from app.services.zoning_source_selector import select_zoning_source_candidates


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DB:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, statement):
        return _Scalars(self.rows)


def _catalog_row(**kwargs):
    defaults = dict(
        id=1,
        municipality="Perth Amboy City",
        label="Zoning Map Links",
        source_url="https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
        source_role="zoning_map",
        authority_tier="municipal_or_state_domain",
        evidence_status="DISCOVERED_CANDIDATE",
        authoritative=False,
        legal_control_confirmed=False,
        active=True,
        current_content_hash="ac388fcc5e50f95d843ea71531b3516a094192d0840a4d20c0085b1d4b7ff505",
        current_status="RETRIEVED",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_catalog_candidate_has_provider_usable_source_identity():
    result = select_zoning_source_candidates(
        municipality="Perth Amboy City",
        db=_DB([_catalog_row()]),
    )
    assert len(result) == 1
    candidate = result[0]
    assert candidate["source_url"].startswith("https://topology.maps.arcgis.com/")
    assert candidate["source_role"] == "zoning_map"
    assert candidate["current_content_hash"]
    assert candidate["current_status"] == "RETRIEVED"


def test_provider_record_preserves_catalog_provenance_without_promoting_authority():
    candidate = select_zoning_source_candidates(
        municipality="Perth Amboy City",
        db=_DB([_catalog_row()]),
    )[0]
    record = ZoningEvidenceRecord(
        municipality=candidate["municipality"],
        block="10",
        lot="2",
        zoning_district="R-10",
        source=candidate,
    )
    adapter_input = record.as_adapter_input()
    assert adapter_input["source"]["source_role"] == "zoning_map"
    assert adapter_input["source"]["authoritative"] is False
    assert adapter_input["source"]["current_content_hash"] == candidate["current_content_hash"]
