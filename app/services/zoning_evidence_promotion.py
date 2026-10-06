"""Controlled promotion guard for dynamic zoning evidence.

Dynamic GIS candidates remain non-authoritative unless the source catalog explicitly
confirms both authority and legal control. This module never fabricates authority.
"""
from __future__ import annotations

from typing import Any


def evaluate_dynamic_zoning_promotion(dynamic_result: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate, but do not silently override, a dynamic zoning candidate."""
    if not dynamic_result:
        return {"status": "VERIFY", "promotable": False, "reason": "NO_DYNAMIC_CANDIDATE"}
    if dynamic_result.get("status") != "ZONING_CANDIDATE_RESOLVED":
        return {"status": "VERIFY", "promotable": False, "reason": "CANDIDATE_NOT_RESOLVED"}

    record = dynamic_result.get("record") or {}
    district = str(record.get("zoning_district") or "").strip()
    source = record.get("source") or {}
    if not district:
        return {"status": "VERIFY", "promotable": False, "reason": "DISTRICT_MISSING"}
    if source.get("authoritative") is not True:
        return {"status": "VERIFY", "promotable": False, "reason": "SOURCE_AUTHORITY_NOT_CONFIRMED"}
    if source.get("legal_control_confirmed") is not True:
        return {"status": "VERIFY", "promotable": False, "reason": "LEGAL_CONTROL_NOT_CONFIRMED"}

    return {
        "status": "ZONING_RESOLVED",
        "promotable": True,
        "reason": "EXPLICIT_AUTHORITY_AND_LEGAL_CONTROL_CONFIRMED",
        "record": record,
    }
