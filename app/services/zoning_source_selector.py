from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.source_catalog import SourceCatalog


_ROLE_PRIORITY = {
    "zoning_map": 0,
    "zoning_ordinance": 1,
    "zoning_administration": 2,
    "municipal_zoning_source": 3,
}

_MUNICIPALITY_SUFFIXES = {
    "city",
    "township",
    "twp",
    "borough",
    "boro",
    "town",
    "village",
}


def _iso_datetime(value: object) -> str | None:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    text = str(value).strip()
    return text or None


def _normalize_municipality(value: object) -> str:
    parts = " ".join(str(value or "").strip().lower().split()).split()
    while parts and parts[-1].rstrip(".,") in _MUNICIPALITY_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def select_zoning_source_candidates(
    *,
    municipality: str,
    db: Any,
) -> list[dict[str, Any]]:
    """Return active catalog sources that may contain zoning evidence.

    Selection is deliberately evidence-neutral: a candidate source is not
    treated as authoritative merely because it was selected. Municipality
    matching is normalization-based so statewide sources can use different
    casing or standard municipal suffixes without requiring per-municipality
    aliases. Stored catalog values are never modified.
    """
    statement = select(SourceCatalog).where(SourceCatalog.active.is_(True))

    # A SQLAlchemy Engine/Connection cannot hydrate ORM entities from an ORM
    # select; use a short-lived Session bound to the connection. Existing test
    # doubles expose ``scalars`` directly, so retain that path for them.
    if isinstance(db, Connection):
        with Session(bind=db) as session:
            rows = session.scalars(statement).all()
    else:
        rows = db.scalars(statement).all()

    requested_key = _normalize_municipality(municipality)
    candidates = [
        row
        for row in rows
        if row.active
        and _normalize_municipality(row.municipality) == requested_key
        and row.source_role in _ROLE_PRIORITY
    ]
    candidates.sort(
        key=lambda row: (
            _ROLE_PRIORITY.get(row.source_role, 99),
            0 if row.authoritative else 1,
            row.label.lower(),
            row.source_url,
        )
    )
    return [
        {
            "id": row.id,
            "municipality": row.municipality,
            "label": row.label,
            "source_url": row.source_url,
            "source_role": row.source_role,
            "authority_tier": row.authority_tier,
            "evidence_status": row.evidence_status,
            "authoritative": bool(row.authoritative),
            "legal_control_confirmed": bool(row.legal_control_confirmed),
            "retrieval_url": getattr(row, "retrieval_url", None),
            "first_discovered_at": _iso_datetime(getattr(row, "first_discovered_at", None)),
            "last_checked_at": _iso_datetime(getattr(row, "last_checked_at", None)),
            "current_content_hash": row.current_content_hash,
            "current_status": row.current_status,
            "discovery_source": getattr(row, "discovery_source", None),
            "source_type": getattr(row, "source_type", None),
        }
        for row in candidates
    ]
