from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_content import SourceContent
from app.models.source_version import SourceVersion
from app.services.source_history import get_cached_source_content
from app.services.source_versioning import SourceSnapshot


def _snapshot(content: bytes) -> SourceSnapshot:
    from app.services.source_versioning import content_hash

    return SourceSnapshot(
        url="https://example.test/zoning.pdf",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        content_hash=content_hash(content),
        byte_size=len(content),
        status_code=200,
        content_type="application/pdf",
        content=content,
    )


def test_persist_source_snapshot_caches_retrieved_content():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceVersion.__table__, SourceContent.__table__])

    snapshot = _snapshot(b"zoning-evidence")
    # Exercise the storage contract directly without requiring application settings.
    with Session(engine) as db:
        from app.services.source_history import record_source_version, record_source_content
        from app.services.source_versioning import SourceChange
        record_source_version(db, snapshot=snapshot, change=SourceChange("INITIAL", False))
        assert record_source_content(db, snapshot=snapshot) is True
        assert get_cached_source_content(db, source_url=snapshot.url, content_hash=snapshot.content_hash) == b"zoning-evidence"


def test_source_content_cache_deduplicates_same_hash():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceContent.__table__])
    snapshot = _snapshot(b"same")
    with Session(engine) as db:
        from app.services.source_history import record_source_content
        assert record_source_content(db, snapshot=snapshot) is True
        assert record_source_content(db, snapshot=snapshot) is False
        rows = db.scalars(select(SourceContent)).all()
        assert len(rows) == 1


def test_source_content_cache_skips_oversized_representation():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine, tables=[SourceContent.__table__])
    from app.services.source_history import record_source_content
    from app.services.source_versioning import content_hash
    content = b"x" * 5_000_001
    snapshot = SourceSnapshot(
        url="https://example.test/large.pdf",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        content_hash=content_hash(content),
        byte_size=len(content),
        status_code=200,
        content_type="application/pdf",
        content=content,
    )
    with Session(engine) as db:
        assert record_source_content(db, snapshot=snapshot) is False
        assert db.scalars(select(SourceContent)).all() == []
