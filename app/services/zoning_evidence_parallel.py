"""Non-breaking bridge for presenting dynamic zoning evidence alongside legacy evidence.

This module deliberately does not replace, mutate, or reinterpret the existing
zoning evidence result. It attaches a separately named dynamic candidate so
callers can inspect it without changing established API contracts.
"""
from __future__ import annotations

from typing import Any


def attach_dynamic_evidence_candidate(
    legacy_evidence: dict[str, Any],
    dynamic_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a copy of legacy evidence with an isolated dynamic candidate.

    The legacy dictionary is never mutated. A dynamic result is informational
    until a later, explicitly tested promotion step validates it.
    """
    result = dict(legacy_evidence)
    if dynamic_result is None:
        return result

    candidate = dict(dynamic_result)
    result["dynamic_evidence_candidate"] = candidate
    return result


def dynamic_candidate_is_promotable(dynamic_result: dict[str, Any] | None) -> bool:
    """Return True only for a fully resolved, authoritative dynamic result."""
    if not dynamic_result:
        return False
    if dynamic_result.get("status") != "ZONING_RESOLVED":
        return False
    record = dynamic_result.get("record") or {}
    district = str(record.get("zoning_district") or "").strip()
    source = record.get("source") or {}
    return bool(district and source.get("authoritative") is True)
