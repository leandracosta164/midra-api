from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_version import SourceVersion
from app.services.source_history import get_latest_source_version, record_source_version
from app.services.source_versioning import SourceSnapshot, SourceChange


def _snapshot(hash_value: str, url: str = "https://example.test/source") -> SourceSnapshot:
    return SourceSnapshot(
        url=url,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        content_hash=hash_value,
        byte_size=len(hash_value),
        status_code=200,
        content_type="text/html",
    )


def test_source_history_persists_and_reads_latest():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceVersion.__table__])

    with Session(engine) as db:
        snapshot = _snapshot("a" * 64)
        row = record_source_version(
            db,
            snapshot=snapshot,
            change=SourceChange(status="INITIAL", changed=False),
            municipality="Howell Township",
            source_type="official_municipal",
            authoritative=True,
        )
        assert row.status == "INITIAL"
        latest = get_latest_source_version(db, snapshot.url)
        assert latest is not None
        assert latest.content_hash == snapshot.content_hash
        assert latest.url == snapshot.url


def test_source_history_retains_versions():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceVersion.__table__])

    with Session(engine) as db:
        first = _snapshot("a" * 64)
        second = _snapshot("b" * 64)
        record_source_version(db, snapshot=first, change=SourceChange("INITIAL", False))
        record_source_version(db, snapshot=second, change=SourceChange("CHANGED", True))
        rows = db.scalars(
            select(SourceVersion).order_by(SourceVersion.id)
        ).all()
        assert len(rows) == 2
        assert rows[1].previous_hash == first.content_hash


def test_source_history_unique_constraint_blocks_duplicate_version():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceVersion.__table__])

    with Session(engine) as db:
        snapshot = _snapshot("a" * 64)
        record_source_version(db, snapshot=snapshot, change=SourceChange("INITIAL", False))
        try:
            record_source_version(db, snapshot=snapshot, change=SourceChange("UNCHANGED", False))
        except Exception:
            db.rollback()
        else:
            raise AssertionError("Duplicate source version should be rejected")
