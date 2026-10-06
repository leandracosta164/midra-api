from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.source_official_representation_orchestration import orchestrate_official_zoning_representations


MUNICIPALITY = "Perth Amboy City"
PAGE = "https://www.perthamboynj.org/zoning"
TARGET = "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c"


def _db(page_content: bytes, *, target_role="zoning_map"):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[SourceCatalog.__table__, SourceContent.__table__])
    db = Session(engine)
    now = datetime.now(timezone.utc)
    page_hash = "a" * 64
    target_hash = "b" * 64
    db.add_all([
        SourceCatalog(municipality=MUNICIPALITY, label="Zoning page", source_url=PAGE, source_role="zoning_administration", authority_tier="municipal", evidence_status="DISCOVERED_CANDIDATE", authoritative=False, legal_control_confirmed=False, active=True, first_discovered_at=now, current_content_hash=page_hash),
        SourceCatalog(municipality=MUNICIPALITY, label="Zoning Map", source_url=TARGET, source_role=target_role, authority_tier="external", evidence_status="DISCOVERED_CANDIDATE", authoritative=False, legal_control_confirmed=False, active=True, first_discovered_at=now, current_content_hash=target_hash),
        SourceContent(source_url=PAGE, content_hash=page_hash, retrieved_at=now, content_type="text/html", byte_size=len(page_content), content=page_content),
        SourceContent(source_url=TARGET, content_hash=target_hash, retrieved_at=now, content_type="text/html", byte_size=6, content=b"viewer"),
    ])
    db.commit()
    return db


def test_orchestration_promotes_exact_official_zoning_target_only():
    db = _db(f'<h1>Zoning Map</h1><a href="{TARGET}">Interactive Zoning Viewer</a>'.encode())
    result = orchestrate_official_zoning_representations(db=db, municipality=MUNICIPALITY)
    target = db.query(SourceCatalog).filter(SourceCatalog.source_url == TARGET).one()
    assert result["promoted_count"] == 1
    assert target.authoritative is True
    assert target.legal_control_confirmed is False
    assert target.evidence_status == "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"


def test_orchestration_does_not_promote_unlinked_target():
    db = _db(b"<h1>Zoning Map</h1><p>Interactive Zoning Viewer</p>")
    result = orchestrate_official_zoning_representations(db=db, municipality=MUNICIPALITY)
    target = db.query(SourceCatalog).filter(SourceCatalog.source_url == TARGET).one()
    assert result["promoted_count"] == 0
    assert target.authoritative is False


def test_orchestration_does_not_treat_non_zoning_map_as_target():
    db = _db(f'<h1>Zoning Map</h1><a href="{TARGET}">viewer</a>'.encode(), target_role="zoning_ordinance")
    result = orchestrate_official_zoning_representations(db=db, municipality=MUNICIPALITY)
    assert result["target_count"] == 0
    assert result["promoted_count"] == 0


def test_orchestration_fails_closed_without_database_interface():
    result = orchestrate_official_zoning_representations(db=object(), municipality=MUNICIPALITY)
    assert result["status"] == "OFFICIAL_REPRESENTATION_ORCHESTRATION_UNAVAILABLE"
    assert result["promoted_count"] == 0


def test_orchestration_matches_municipality_case_without_weakening_target_identity():
    db = _db(f'<h1>Zoning Map</h1><a href="{TARGET}">Interactive Zoning Viewer</a>'.encode())
    result = orchestrate_official_zoning_representations(db=db, municipality="PERTH AMBOY CITY")
    assert result["promoted_count"] == 1
