"""Persist and invalidate explicit legal-control verification conservatively.

A catalog row may be promoted only from a successful strict target binding and
only while both the target and controlling-evidence fingerprints are known.
The stored fingerprints make trust revocable when either representation changes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.models.source_catalog import SourceCatalog


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def legal_control_promotion_decision(*, binding: dict[str, Any] | None, authoritative: bool,
                                     target_content_hash: str | None, legal_content_hash: str | None) -> dict[str, Any]:
    binding = dict(binding or {})
    if binding.get("status") != "LEGAL_CONTROL_TARGET_BOUND" or binding.get("legal_control_confirmed") is not True:
        return {"promotable": False, "reason": "STRICT_TARGET_BINDING_REQUIRED"}
    if authoritative is not True:
        return {"promotable": False, "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED"}
    if not target_content_hash or not legal_content_hash:
        return {"promotable": False, "reason": "VERSION_FINGERPRINT_REQUIRED"}
    return {"promotable": True, "reason": "EXPLICIT_LEGAL_CONTROL_VERIFIED"}


def confirm_catalog_legal_control(*, db: Any, municipality: str, target_source_url: str,
                                  binding: dict[str, Any], target_content_hash: str,
                                  legal_source_url: str, legal_content_hash: str,
                                  verified_at: datetime | None = None) -> dict[str, Any]:
    row = db.scalar(select(SourceCatalog).where(
        SourceCatalog.municipality == municipality,
        SourceCatalog.source_url == target_source_url,
    ).limit(1))
    if row is None:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "reason": "CATALOG_TARGET_NOT_FOUND"}

    decision = legal_control_promotion_decision(
        binding=binding,
        authoritative=row.authoritative is True,
        target_content_hash=target_content_hash,
        legal_content_hash=legal_content_hash,
    )
    if not decision["promotable"]:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", **decision}
    if row.current_content_hash != target_content_hash:
        return {"status": "LEGAL_CONTROL_NOT_PROMOTED", "promotable": False, "reason": "TARGET_VERSION_MISMATCH"}

    row.legal_control_confirmed = True
    row.legal_control_verified_at = verified_at or _utc_now()
    row.legal_control_target_hash = target_content_hash
    row.legal_control_evidence_url = legal_source_url
    row.legal_control_evidence_hash = legal_content_hash
    row.legal_control_matched_reference = binding.get("matched_reference")
    db.commit()
    return {"status": "LEGAL_CONTROL_PROMOTED", "promotable": True, "reason": decision["reason"]}


def clear_legal_control(row: SourceCatalog) -> None:
    row.legal_control_confirmed = False
    row.legal_control_verified_at = None
    row.legal_control_target_hash = None
    row.legal_control_evidence_url = None
    row.legal_control_evidence_hash = None
    row.legal_control_matched_reference = None


def invalidate_changed_legal_control(*, db: Any, source_url: str, new_content_hash: str | None,
                                     retrieval_url: str | None = None) -> int:
    """Revoke verifications whose target or legal evidence changed."""
    if not new_content_hash:
        return 0
    rows = db.scalars(select(SourceCatalog).where(SourceCatalog.legal_control_confirmed.is_(True))).all()
    invalidated = 0
    identities = {value for value in (source_url, retrieval_url) if value}
    for row in rows:
        row_identities = {value for value in (row.source_url, row.retrieval_url) if value}
        target_changed = bool(row_identities & identities) and row.legal_control_target_hash not in {None, new_content_hash}
        evidence_row = db.scalar(select(SourceCatalog).where(SourceCatalog.source_url == row.legal_control_evidence_url).limit(1)) if row.legal_control_evidence_url else None
        evidence_identities = {row.legal_control_evidence_url}
        if evidence_row is not None and evidence_row.retrieval_url:
            evidence_identities.add(evidence_row.retrieval_url)
        evidence_changed = bool(evidence_identities & identities) and row.legal_control_evidence_hash not in {None, new_content_hash}
        if target_changed or evidence_changed:
            clear_legal_control(row)
            invalidated += 1
    if invalidated:
        db.commit()
    return invalidated
