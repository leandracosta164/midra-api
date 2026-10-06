"""Guarded persistence for independently verified official zoning representations."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.source_catalog import SourceCatalog


def confirm_catalog_official_representation(
    *,
    db: Any,
    municipality: str,
    target_source_url: str,
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Persist official-publication authority without asserting legal control."""
    evidence = dict(evidence or {})
    if evidence.get("status") != "OFFICIAL_ZONING_REPRESENTATION_VERIFIED" or evidence.get("authority_verified") is not True:
        return {"status": "SOURCE_AUTHORITY_NOT_PROMOTED", "reason": "OFFICIAL_REPRESENTATION_EVIDENCE_REQUIRED"}
    if evidence.get("legal_control_confirmed") is True:
        return {"status": "SOURCE_AUTHORITY_NOT_PROMOTED", "reason": "REPRESENTATION_EVIDENCE_MUST_NOT_ASSERT_LEGAL_CONTROL"}

    target = evidence.get("target_source") or {}
    evidence_url = str(target.get("source_url") or target.get("url") or "").strip()
    if evidence_url != str(target_source_url or "").strip():
        return {"status": "SOURCE_AUTHORITY_NOT_PROMOTED", "reason": "EVIDENCE_TARGET_MISMATCH"}

    row = db.scalar(
        select(SourceCatalog).where(
            SourceCatalog.municipality == municipality,
            SourceCatalog.source_url == target_source_url,
            SourceCatalog.active.is_(True),
        ).limit(1)
    )
    if row is None:
        return {"status": "SOURCE_AUTHORITY_NOT_PROMOTED", "reason": "CATALOG_TARGET_NOT_FOUND"}

    row.authoritative = True
    row.evidence_status = "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"
    # This operation is deliberately independent from legal-control verification.
    # Never promote legal control here and never clear an already separately verified
    # legal-control state.
    db.commit()
    return {
        "status": "SOURCE_AUTHORITY_PROMOTED",
        "reason": "OFFICIAL_MUNICIPAL_ZONING_REPRESENTATION_VERIFIED",
        "source_url": row.source_url,
        "authoritative": row.authoritative is True,
        "legal_control_confirmed": row.legal_control_confirmed is True,
    }
