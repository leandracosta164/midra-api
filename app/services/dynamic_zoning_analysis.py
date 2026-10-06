"""On-demand orchestration for dynamic zoning candidates.

This service deliberately remains outside the established property-intelligence
zoning path. It refreshes the discovered municipal source catalog for the
requested municipality, then follows the explicit ArcGIS zoning chain when
available. Dynamic results remain candidates unless the promotion guard
explicitly confirms authority and legal control.
"""
from __future__ import annotations

from typing import Any, Callable

from app.services.municipality_source_refresh import refresh_discovered_municipality_sources
from app.services.zoning_evidence_promotion import evaluate_dynamic_zoning_promotion
from app.services.zoning_spatial_bridge import resolve_dynamic_spatial_zoning_candidate
from app.services.source_official_representation_orchestration import orchestrate_official_zoning_representations
from app.services.source_legal_control_orchestration import orchestrate_municipality_legal_control


def build_dynamic_zoning_evidence(
    candidate: dict[str, Any] | None,
    promotion: dict[str, Any] | None,
) -> dict[str, Any]:
    """Expose dynamic zoning provenance without asserting legal authority."""
    candidate = candidate or {}
    promotion = promotion or {}
    record = candidate.get("record") or {}
    source = record.get("source") or {}
    return {
        "status": promotion.get("status", "VERIFY"),
        "candidate_status": candidate.get("status", "ZONING_NOT_RESOLVED"),
        "promotable": promotion.get("promotable", False),
        "reason": promotion.get("reason"),
        "municipality": record.get("municipality"),
        "block": record.get("block"),
        "lot": record.get("lot"),
        "zoning_district": record.get("zoning_district"),
        "evidence_type": record.get("evidence_type"),
        "mapped_geometries": record.get("mapped_geometries") or [],
        "geometry_role": record.get("geometry_role"),
        "geometry_definitive": False,
        "source": source,
    }


def analyze_dynamic_zoning_candidate(
    *,
    municipality: str,
    block: str,
    lot: str,
    geometry: dict[str, Any],
    db: Any,
    refresh_sources: Callable[..., dict[str, Any]] = refresh_discovered_municipality_sources,
    resolve_candidate: Callable[..., dict[str, Any]] = resolve_dynamic_spatial_zoning_candidate,
    promote_candidate: Callable[[dict[str, Any] | None], dict[str, Any]] = evaluate_dynamic_zoning_promotion,
    authority_orchestrator: Callable[..., dict[str, Any]] = orchestrate_official_zoning_representations,
    legal_control_orchestrator: Callable[..., dict[str, Any]] = orchestrate_municipality_legal_control,
) -> dict[str, Any]:
    """Refresh sources and evaluate a dynamic zoning candidate on demand."""
    if not str(municipality or "").strip():
        return {
            "status": "VERIFY",
            "candidate": None,
            "promotion": {"status": "VERIFY", "promotable": False, "reason": "MUNICIPALITY_MISSING"},
        }

    if not str(block or "").strip() or not str(lot or "").strip() or not geometry:
        return {
            "status": "VERIFY",
            "candidate": None,
            "promotion": {"status": "VERIFY", "promotable": False, "reason": "PARCEL_GEOMETRY_OR_IDENTITY_MISSING"},
        }

    refresh = refresh_sources(municipality)
    canonical_municipality = str(refresh.get("canonical_name") or municipality).strip() or municipality
    authority = authority_orchestrator(db=db, municipality=canonical_municipality)
    legal_control = legal_control_orchestrator(db=db, municipality=canonical_municipality)
    candidate = resolve_candidate(
        municipality=municipality,
        block=str(block),
        lot=str(lot),
        geometry=geometry,
        db=db,
    )
    promotion = promote_candidate(candidate)

    return {
        "status": promotion.get("status", "VERIFY"),
        "refresh": refresh,
        "official_representation": authority,
        "legal_control": legal_control,
        "candidate": candidate,
        "promotion": promotion,
        "evidence": build_dynamic_zoning_evidence(candidate, promotion),
    }
