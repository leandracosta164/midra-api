"""Persistent source-version history for MIDRA public evidence."""

from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.source_version import SourceVersion
from app.models.source_content import SourceContent
from app.services.source_versioning import SourceChange, SourceSnapshot, compare_snapshots

logger = logging.getLogger(__name__)

MAX_CACHED_SOURCE_BYTES = 5_000_000


def _as_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def get_latest_source_version(
    db: Session,
    source_url: str,
) -> SourceSnapshot | None:
    """Return the latest persisted snapshot for a source URL."""
    row = db.scalar(
        select(SourceVersion)
        .where(SourceVersion.source_url == source_url)
        .order_by(SourceVersion.retrieved_at.desc(), SourceVersion.id.desc())
        .limit(1)
    )
    if row is None:
        return None
    return SourceSnapshot(
        url=row.source_url,
        retrieved_at=row.retrieved_at.isoformat(),
        content_hash=row.content_hash,
        byte_size=row.byte_size,
        status_code=row.status_code,
        content_type=row.content_type or "",
        etag=row.etag,
        last_modified=row.last_modified,
        content=None,
    )


def record_source_version(
    db: Session,
    *,
    snapshot: SourceSnapshot,
    change: SourceChange,
    municipality: str | None = None,
    source_type: str | None = None,
    description: str | None = None,
    authoritative: bool = False,
) -> SourceVersion:
    """Persist a source snapshot and its change classification."""
    previous = get_latest_source_version(db, snapshot.url)
    row = SourceVersion(
        source_url=snapshot.url,
        municipality=municipality,
        source_type=source_type,
        description=description,
        authoritative=authoritative,
        retrieved_at=_as_datetime(snapshot.retrieved_at),
        status=change.status,
        content_hash=snapshot.content_hash,
        byte_size=snapshot.byte_size,
        status_code=snapshot.status_code,
        content_type=snapshot.content_type or None,
        etag=snapshot.etag,
        last_modified=snapshot.last_modified,
        previous_hash=previous.content_hash if previous else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_cached_source_content(
    db: Session,
    *,
    source_url: str,
    content_hash: str,
) -> bytes | None:
    """Return cached bytes for an exact source URL/content hash."""
    row = db.scalar(
        select(SourceContent)
        .where(
            SourceContent.source_url == source_url,
            SourceContent.content_hash == content_hash,
        )
        .limit(1)
    )
    return row.content if row is not None else None


def record_source_content(
    db: Session,
    *,
    snapshot: SourceSnapshot,
) -> bool:
    """Cache a retrieved representation once, keyed by URL and content hash."""
    if snapshot.content is None or snapshot.byte_size > MAX_CACHED_SOURCE_BYTES:
        return False
    existing = get_cached_source_content(
        db, source_url=snapshot.url, content_hash=snapshot.content_hash
    )
    if existing is not None:
        return False
    row = SourceContent(
        source_url=snapshot.url,
        content_hash=snapshot.content_hash,
        retrieved_at=_as_datetime(snapshot.retrieved_at),
        content_type=snapshot.content_type or None,
        byte_size=snapshot.byte_size,
        content=snapshot.content,
    )
    db.add(row)
    db.commit()
    return True


def ensure_source_history_schema() -> None:
    """Create only the source-history table if it is not present."""
    from app.db.database import engine

    Base.metadata.create_all(bind=engine, tables=[SourceVersion.__table__, SourceContent.__table__])


def persist_source_snapshot(
    *,
    snapshot: SourceSnapshot,
    municipality: str | None = None,
    source_type: str | None = None,
    description: str | None = None,
    authoritative: bool = False,
) -> SourceChange:
    """Persist a snapshot using the application DB, without affecting retrieval."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        ensure_source_history_schema()
        previous = get_latest_source_version(db, snapshot.url)
        change = compare_snapshots(previous, snapshot)
        if change.status == "UNCHANGED":
            if snapshot.content is not None:
                record_source_content(db, snapshot=snapshot)
            return change
        record_source_version(
            db,
            snapshot=snapshot,
            change=change,
            municipality=municipality,
            source_type=source_type,
            description=description,
            authoritative=authoritative,
        )
        if snapshot.content is not None:
            record_source_content(db, snapshot=snapshot)
        return change
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("MIDRA source history persistence unavailable: %s", exc)
        return SourceChange(status="HISTORY_UNAVAILABLE", changed=False)
    finally:
        db.close()
