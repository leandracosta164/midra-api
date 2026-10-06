from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.source_legal_control_orchestration import (
    orchestrate_municipality_legal_control,
    verify_catalog_legal_control,
)
from app.services.source_versioning import content_hash


MUNICIPALITY = "Test Borough"
TARGET = "https://maps.test.gov/apps/instant/basic/index.html?appid=0123456789abcdef0123456789abcdef"
LEGAL = "https://test.gov/code/zoning"


def _row(url, role, content, *, authoritative=False):
    digest = content_hash(content)
    return SourceCatalog(
        municipality=MUNICIPALITY,
        label="Official Zoning Map" if role == "zoning_map" else "Zoning Ordinance",
        source_url=url,
        source_role=role,
        authority_tier="likely_municipal_or_state_domain",
        evidence_status="DISCOVERED_CANDIDATE",
        authoritative=authoritative,
        legal_control_confirmed=False,
        active=True,
        first_discovered_at=datetime.now(timezone.utc),
        current_content_hash=digest,
    ), SourceContent(
        source_url=url,
        content_hash=digest,
        retrieved_at=datetime.now(timezone.utc),
        content_type="text/html",
        byte_size=len(content),
        content=content,
    )


def _db(*, target_authoritative=True, legal_text=None, include_target_content=True, include_legal_content=True):
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceCatalog.__table__, SourceContent.__table__])
    db = Session(engine)
    target_row, target_content = _row(TARGET, "zoning_map", b"map representation", authoritative=target_authoritative)
    text = legal_text or (
        b'This chapter adopts the Official Zoning Map. The original map shall be used as the final authority. '
        b'The controlling digital reference is https://maps.test.gov/apps/instant/basic/index.html?appid=0123456789abcdef0123456789abcdef.'
    )
    legal_row, legal_content = _row(LEGAL, "zoning_ordinance", text)
    db.add_all([target_row, legal_row])
    if include_target_content:
        db.add(target_content)
    if include_legal_content:
        db.add(legal_content)
    db.commit()
    return db


def test_orchestration_promotes_only_explicit_authoritative_versioned_binding():
    db = _db()
    try:
        result = orchestrate_municipality_legal_control(db=db, municipality=MUNICIPALITY)
        assert result["promoted_count"] == 1
        target = db.query(SourceCatalog).filter_by(source_url=TARGET).one()
        assert target.legal_control_confirmed is True
        assert target.legal_control_evidence_url == LEGAL
        assert target.legal_control_target_hash == target.current_content_hash
    finally:
        db.close()


def test_orchestration_does_not_infer_authority():
    db = _db(target_authoritative=False)
    try:
        result = orchestrate_municipality_legal_control(db=db, municipality=MUNICIPALITY)
        assert result["promoted_count"] == 0
        assert result["attempts"][0]["reason"] == "SOURCE_AUTHORITY_NOT_CONFIRMED"
    finally:
        db.close()


def test_verification_requires_current_target_content_cache():
    db = _db(include_target_content=False)
    try:
        result = verify_catalog_legal_control(db=db, municipality=MUNICIPALITY, target_source_url=TARGET, legal_source_url=LEGAL)
        assert result["reason"] == "CURRENT_TARGET_CONTENT_NOT_CACHED"
    finally:
        db.close()


def test_verification_requires_current_legal_content_cache():
    db = _db(include_legal_content=False)
    try:
        result = verify_catalog_legal_control(db=db, municipality=MUNICIPALITY, target_source_url=TARGET, legal_source_url=LEGAL)
        assert result["reason"] == "CURRENT_LEGAL_CONTENT_NOT_CACHED"
    finally:
        db.close()


def test_orchestration_refuses_title_or_domain_similarity_without_explicit_target_identity():
    legal_text = b"This chapter adopts the Official Zoning Map. The original map shall be used as the final authority."
    db = _db(legal_text=legal_text)
    try:
        result = orchestrate_municipality_legal_control(db=db, municipality=MUNICIPALITY)
        assert result["promoted_count"] == 0
        assert result["attempts"][0]["reason"] == "TARGET_IDENTITY_NOT_EXPLICITLY_REFERENCED"
    finally:
        db.close()


def test_orchestration_matches_municipality_case_insensitively():
    db = _db()
    try:
        result = orchestrate_municipality_legal_control(db=db, municipality="  TEST   BOROUGH ")
        assert result["target_count"] == 1
        assert result["legal_source_count"] == 1
        assert result["promoted_count"] == 1
    finally:
        db.close()
