"""Automatic, evidence-preserving promotion of official zoning representations.

This composes Phase 5.13 with the current source catalog/cache.  It may promote
``authoritative`` only when a cached official municipal page explicitly presents
an exact cataloged zoning-map target.  It never promotes legal control.
"""
from __future__ import annotations

from typing import Any
import re

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.source_official_representation import evaluate_official_zoning_representation
from app.services.source_official_representation_state import confirm_catalog_official_representation


def _normalize_municipality(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


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


def orchestrate_official_zoning_representations(*, db: Any, municipality: str) -> dict[str, Any]:
    """Evaluate cached municipal pages against exact cataloged zoning-map targets.

    The operation is deliberately narrow: source-role selection creates candidates
    only.  Every promotion still requires the Phase 5.13 official-page, zoning-
    context, and exact-target-reference checks.
    """
    scalars = getattr(db, "scalars", None)
    scalar = getattr(db, "scalar", None)
    if not callable(scalars) or not callable(scalar):
        return {
            "status": "OFFICIAL_REPRESENTATION_ORCHESTRATION_UNAVAILABLE",
            "municipality": municipality,
            "reason": "DB_QUERY_INTERFACE_UNAVAILABLE",
            "promoted_count": 0,
            "attempts": [],
        }

    try:
        rows = scalars(
            select(SourceCatalog).where(SourceCatalog.active.is_(True))
        ).all()
        requested = _normalize_municipality(municipality)
        rows = [row for row in rows if _normalize_municipality(row.municipality) == requested]
    except SQLAlchemyError:
        return {
            "status": "OFFICIAL_REPRESENTATION_ORCHESTRATION_UNAVAILABLE",
            "municipality": municipality,
            "reason": "CATALOG_QUERY_UNAVAILABLE",
            "promoted_count": 0,
            "attempts": [],
        }

    targets = [row for row in rows if row.source_role == "zoning_map"]
    pages: list[tuple[SourceCatalog, bytes]] = []
    for row in rows:
        if not row.current_content_hash:
            continue
        try:
            content = _current_content(db=db, row=row)
        except SQLAlchemyError:
            content = None
        if content:
            pages.append((row, content))

    attempts: list[dict[str, Any]] = []
    promoted_urls: set[str] = set()
    for target in targets:
        if target.authoritative is True:
            continue
        for page, content in pages:
            if page.source_url == target.source_url:
                continue
            evidence = evaluate_official_zoning_representation(
                municipality=target.municipality,
                official_page_url=page.source_url,
                official_page_content=content,
                target_source={
                    "source_url": target.source_url,
                    "retrieval_url": target.retrieval_url,
                    "label": target.label,
                    "source_role": target.source_role,
                },
            )
            attempts.append({
                "official_page_url": page.source_url,
                "target_source_url": target.source_url,
                "status": evidence.get("status"),
                "reason": evidence.get("reason"),
            })
            if evidence.get("status") != "OFFICIAL_ZONING_REPRESENTATION_VERIFIED":
                continue
            result = confirm_catalog_official_representation(
                db=db,
                municipality=target.municipality,
                target_source_url=target.source_url,
                evidence=evidence,
            )
            if result.get("status") == "SOURCE_AUTHORITY_PROMOTED":
                promoted_urls.add(target.source_url)
                break

    return {
        "status": "OFFICIAL_REPRESENTATION_ORCHESTRATION_COMPLETE",
        "municipality": municipality,
        "target_count": len(targets),
        "cached_page_count": len(pages),
        "attempt_count": len(attempts),
        "promoted_count": len(promoted_urls),
        "promoted_source_urls": sorted(promoted_urls),
        "attempts": attempts,
    }
