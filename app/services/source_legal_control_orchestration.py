"""Conservative orchestration for versioned legal-control verification.

This layer composes the already-verified Phase 5.8 extraction, Phase 5.9 strict
binding, and Phase 5.10 versioned promotion contracts.  It does not infer
source authority and it does not guess source identity.  Promotion is possible
only when the catalog already contains an independently authoritative target,
both exact current representations are cached, and the controlling legal text
explicitly identifies that target.
"""
from __future__ import annotations

from typing import Any
import re

from sqlalchemy import select

from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.source_legal_control_binding import bind_legal_control_to_source
from app.services.source_legal_control_state import confirm_catalog_legal_control


def _normalize_municipality(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _catalog_row(*, db: Any, municipality: str, source_url: str) -> SourceCatalog | None:
    requested = _normalize_municipality(municipality)
    rows = db.scalars(
        select(SourceCatalog).where(
            SourceCatalog.source_url == source_url,
            SourceCatalog.active.is_(True),
        )
    ).all()
    return next((row for row in rows if _normalize_municipality(row.municipality) == requested), None)


def _current_content(*, db: Any, row: SourceCatalog) -> bytes | None:
    if not row.current_content_hash:
        return None
    cached = db.scalar(
        select(SourceContent).where(
            SourceContent.source_url == (row.retrieval_url or row.source_url),
            SourceContent.content_hash == row.current_content_hash,
        ).limit(1)
    )
    return cached.content if cached is not None else None


def verify_catalog_legal_control(
    *,
    db: Any,
    municipality: str,
    target_source_url: str,
    legal_source_url: str,
) -> dict[str, Any]:
    """Attempt one exact target/evidence verification using current cached versions.

    This function is intentionally fail-closed.  It never changes ``authoritative``
    and delegates persistence to the Phase 5.10 promotion guard only after strict
    Phase 5.9 binding succeeds.
    """
    target = _catalog_row(db=db, municipality=municipality, source_url=target_source_url)
    if target is None:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "CATALOG_TARGET_NOT_FOUND"}

    legal = _catalog_row(db=db, municipality=municipality, source_url=legal_source_url)
    if legal is None:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "LEGAL_EVIDENCE_SOURCE_NOT_FOUND"}

    if target.authoritative is not True:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED"}

    target_content = _current_content(db=db, row=target)
    if target_content is None:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "CURRENT_TARGET_CONTENT_NOT_CACHED"}

    legal_content = _current_content(db=db, row=legal)
    if legal_content is None:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "CURRENT_LEGAL_CONTENT_NOT_CACHED"}

    binding = bind_legal_control_to_source(
        legal_content=legal_content,
        target_source={
            "source_url": target.source_url,
            "label": target.label,
            "source_role": target.source_role,
            "authoritative": target.authoritative is True,
        },
        legal_source_url=legal.source_url,
    )
    if binding.get("status") != "LEGAL_CONTROL_TARGET_BOUND":
        return {
            "status": "LEGAL_CONTROL_NOT_PROMOTED",
            "reason": binding.get("reason", "STRICT_TARGET_BINDING_REQUIRED"),
            "binding": binding,
        }

    result = confirm_catalog_legal_control(
        db=db,
        municipality=target.municipality,
        target_source_url=target.source_url,
        binding=binding,
        target_content_hash=target.current_content_hash,
        legal_source_url=legal.source_url,
        legal_content_hash=legal.current_content_hash,
    )
    return {**result, "binding": binding}


def orchestrate_municipality_legal_control(*, db: Any, municipality: str) -> dict[str, Any]:
    """Try all explicit current zoning-map/ordinance pairs for one municipality.

    Candidate pairing is role-based only; role selection itself grants no trust.
    Each pair still has to pass independent authority, cached-version, explicit
    legal-text, exact-target-binding, and versioned-promotion guards.
    """
    scalars = getattr(db, "scalars", None)
    if not callable(scalars):
        return {
            "status": "LEGAL_CONTROL_ORCHESTRATION_UNAVAILABLE",
            "municipality": municipality,
            "reason": "DB_QUERY_INTERFACE_UNAVAILABLE",
            "target_count": 0,
            "legal_source_count": 0,
            "attempt_count": 0,
            "promoted_count": 0,
            "attempts": [],
        }
    rows = db.scalars(
        select(SourceCatalog).where(SourceCatalog.active.is_(True))
    ).all()
    requested = _normalize_municipality(municipality)
    rows = [row for row in rows if _normalize_municipality(row.municipality) == requested]
    targets = [row for row in rows if row.source_role == "zoning_map"]
    legal_sources = [row for row in rows if row.source_role == "zoning_ordinance"]

    attempts: list[dict[str, Any]] = []
    promoted = 0
    for target in targets:
        for legal in legal_sources:
            result = verify_catalog_legal_control(
                db=db,
                municipality=municipality,
                target_source_url=target.source_url,
                legal_source_url=legal.source_url,
            )
            attempts.append({
                "target_source_url": target.source_url,
                "legal_source_url": legal.source_url,
                "status": result.get("status"),
                "reason": result.get("reason"),
            })
            if result.get("status") == "LEGAL_CONTROL_PROMOTED":
                promoted += 1

    return {
        "status": "LEGAL_CONTROL_ORCHESTRATION_COMPLETE",
        "municipality": municipality,
        "target_count": len(targets),
        "legal_source_count": len(legal_sources),
        "attempt_count": len(attempts),
        "promoted_count": promoted,
        "attempts": attempts,
    }
