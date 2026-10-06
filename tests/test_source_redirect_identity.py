from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.source_legal_control_orchestration import verify_catalog_legal_control
from app.services.source_legal_control_state import invalidate_changed_legal_control
from app.services.source_versioning import content_hash

M = "Test Borough"
TARGET = "https://test.gov/zoning-map"
TARGET_FINAL = "https://cdn.test.gov/maps/current"
LEGAL = "https://test.gov/zoning-code"
LEGAL_FINAL = "https://ecode.test.gov/123"


def _row(url, retrieval_url, role, content, authoritative=False):
    h = content_hash(content)
    return SourceCatalog(
        municipality=M, label=role, source_url=url, retrieval_url=retrieval_url,
        source_role=role, authority_tier="municipal", evidence_status="DISCOVERED_CANDIDATE",
        authoritative=authoritative, legal_control_confirmed=False, active=True,
        first_discovered_at=datetime.now(timezone.utc), current_content_hash=h,
    ), SourceContent(
        source_url=retrieval_url, content_hash=h, retrieved_at=datetime.now(timezone.utc),
        content_type="text/html", byte_size=len(content), content=content,
    )


def _db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceCatalog.__table__, SourceContent.__table__])
    db = Session(engine)
    target, target_content = _row(TARGET, TARGET_FINAL, "zoning_map", b"map", True)
    legal_text = (b"This chapter adopts the Official Zoning Map. The original map shall be used as the final authority. "
                  + f"The controlling digital reference is {TARGET}.".encode())
    legal, legal_content = _row(LEGAL, LEGAL_FINAL, "zoning_ordinance", legal_text)
    db.add_all([target, legal, target_content, legal_content]); db.commit()
    return db


def test_verification_uses_exact_recorded_retrieval_url_for_cached_content():
    db = _db()
    try:
        result = verify_catalog_legal_control(db=db, municipality=M, target_source_url=TARGET, legal_source_url=LEGAL)
        assert result["status"] == "LEGAL_CONTROL_PROMOTED"
    finally:
        db.close()


def test_discovered_source_url_remains_binding_identity_after_redirect():
    db = _db()
    try:
        result = verify_catalog_legal_control(db=db, municipality=M, target_source_url=TARGET, legal_source_url=LEGAL)
        assert result["binding"]["matched_reference"] == TARGET
    finally:
        db.close()


def test_redirect_target_change_invalidates_verified_target():
    db = _db()
    try:
        assert verify_catalog_legal_control(db=db, municipality=M, target_source_url=TARGET, legal_source_url=LEGAL)["status"] == "LEGAL_CONTROL_PROMOTED"
        count = invalidate_changed_legal_control(db=db, source_url=TARGET, retrieval_url=TARGET_FINAL, new_content_hash="f" * 64)
        assert count == 1
        assert db.query(SourceCatalog).filter_by(source_url=TARGET).one().legal_control_confirmed is False
    finally:
        db.close()


def test_redirected_legal_evidence_change_invalidates_verified_target():
    db = _db()
    try:
        assert verify_catalog_legal_control(db=db, municipality=M, target_source_url=TARGET, legal_source_url=LEGAL)["status"] == "LEGAL_CONTROL_PROMOTED"
        count = invalidate_changed_legal_control(db=db, source_url=LEGAL, retrieval_url=LEGAL_FINAL, new_content_hash="e" * 64)
        assert count == 1
    finally:
        db.close()


def test_unrelated_redirect_identity_does_not_invalidate_verification():
    db = _db()
    try:
        assert verify_catalog_legal_control(db=db, municipality=M, target_source_url=TARGET, legal_source_url=LEGAL)["status"] == "LEGAL_CONTROL_PROMOTED"
        count = invalidate_changed_legal_control(db=db, source_url="https://other.test/a", retrieval_url="https://other.test/b", new_content_hash="d" * 64)
        assert count == 0
        assert db.query(SourceCatalog).filter_by(source_url=TARGET).one().legal_control_confirmed is True
    finally:
        db.close()
