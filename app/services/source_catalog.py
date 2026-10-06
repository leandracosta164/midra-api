"""Persistent catalog for discovered municipal public sources."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.models.source_catalog import SourceCatalog
from app.services.source_legal_control_state import invalidate_changed_legal_control


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_source_catalog_schema() -> None:
    from app.db.database import engine
    Base.metadata.create_all(bind=engine, tables=[SourceCatalog.__table__])


def upsert_source_catalog_entry(
    *,
    municipality: str,
    label: str,
    source_url: str,
    classification: dict,
    source: dict | None = None,
    retrieved_at: datetime | None = None,
    content_hash: str | None = None,
    current_status: str | None = None,
    retrieval_url: str | None = None,
) -> bool:
    """Create/update catalog metadata; never assert legal control."""
    from app.db.session import SessionLocal

    source = source or {}
    now = retrieved_at or _utc_now()
    db = SessionLocal()
    try:
        ensure_source_catalog_schema()
        row = db.scalar(
            select(SourceCatalog)
            .where(SourceCatalog.municipality == municipality)
            .where(SourceCatalog.source_url == source_url)
            .limit(1)
        )
        if row is None:
            row = SourceCatalog(
                municipality=municipality,
                label=label,
                source_url=source_url,
                retrieval_url=retrieval_url,
                source_role=classification.get("source_role", "municipal_zoning_source"),
                authority_tier=classification.get("authority_tier", "external_or_unknown_domain"),
                evidence_status=classification.get("evidence_status", "DISCOVERED_CANDIDATE"),
                discovery_source=source.get("discovered_from"),
                source_type=source.get("source_type"),
                authoritative=False,
                legal_control_confirmed=False,
                active=True,
                first_discovered_at=now,
            )
            db.add(row)
        else:
            row.label = label
            row.source_role = classification.get("source_role", row.source_role)
            row.authority_tier = classification.get("authority_tier", row.authority_tier)
            row.evidence_status = classification.get("evidence_status", row.evidence_status)
            row.discovery_source = source.get("discovered_from") or row.discovery_source
            row.source_type = source.get("source_type") or row.source_type
            row.active = True
            if retrieval_url:
                row.retrieval_url = retrieval_url

        # A verified legal-control binding is version-specific. If either this
        # source itself or controlling evidence referenced by another catalog row
        # changes, revoke that verification before recording the new fingerprint.
        if content_hash:
            invalidate_changed_legal_control(
                db=db, source_url=source_url, retrieval_url=retrieval_url, new_content_hash=content_hash
            )

        row.last_checked_at = now
        row.current_content_hash = content_hash or row.current_content_hash
        row.current_status = current_status or row.current_status
        row.notes = " ".join(classification.get("classification_notes", [])) or row.notes
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        return False
    finally:
        db.close()
