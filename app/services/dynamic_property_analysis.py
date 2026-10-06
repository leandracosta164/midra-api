"""Non-breaking end-to-end bridge for dynamic property intelligence.

This service composes the already-verified dynamic zoning, project-applicability,
and approval-pathway layers without changing the established property-intelligence
API. Dynamic zoning must first be promotable before downstream dynamic project or
approval evidence can be considered.
"""
from __future__ import annotations

from typing import Any, Callable

from app.models.source_catalog import SourceCatalog
from app.models.source_content import SourceContent
from app.services.dynamic_approval_pathway import evaluate_dynamic_approval_pathway
from app.services.dynamic_approval_pathway_discovery import discover_dynamic_approval_pathway_candidate
from app.services.dynamic_project_rule_discovery import discover_dynamic_project_rule_candidate
from app.services.dynamic_project_applicability import evaluate_dynamic_project_applicability
from app.services.dynamic_zoning_analysis import analyze_dynamic_zoning_candidate
from app.services.project_intent_normalization import interpret_project_intent


def _verify(reason: str) -> dict[str, Any]:
    return {
        "status": "VERIFY",
        "applicable": False,
        "promotable": False,
        "reason": reason,
    }


def _normalize_municipality(value: str) -> str:
    import re
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _load_dynamic_source_documents(db: Any, municipality: str) -> list[dict[str, Any]]:
    """Load active cached source documents for dynamic rule discovery, read-only."""
    query = getattr(db, "query", None)
    if not callable(query):
        return []
    try:
        rows = (
            query(SourceCatalog, SourceContent)
            .join(SourceContent, SourceContent.source_url == SourceCatalog.source_url)
            .filter(SourceCatalog.active.is_(True))
            .all()
        )
    except Exception:
        return []

    target = _normalize_municipality(municipality)
    documents: list[dict[str, Any]] = []
    for catalog, content in rows:
        if _normalize_municipality(catalog.municipality) != target:
            continue
        raw = content.content
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "ignore")
        documents.append({
            "source_url": content.source_url,
            "label": catalog.label,
            "source_role": catalog.source_role,
            "authority_tier": catalog.authority_tier,
            "evidence_status": catalog.evidence_status,
            "discovery_source": catalog.discovery_source,
            "source_type": catalog.source_type,
            "authoritative": catalog.authoritative,
            "legal_control_confirmed": catalog.legal_control_confirmed,
            "content": str(raw or ""),
        })
    return documents


def analyze_dynamic_property(
    *,
    municipality: str,
    block: str,
    lot: str,
    geometry: dict[str, Any],
    project_goal: str,
    db: Any,
    zoning_analysis: Callable[..., dict[str, Any]] = analyze_dynamic_zoning_candidate,
    project_evaluator: Callable[..., dict[str, Any]] = evaluate_dynamic_project_applicability,
    project_rule_discoverer: Callable[..., dict[str, Any]] = discover_dynamic_project_rule_candidate,
    approval_pathway_discoverer: Callable[..., dict[str, Any] | None] = discover_dynamic_approval_pathway_candidate,
    approval_evaluator: Callable[[dict[str, Any] | None], dict[str, Any]] = evaluate_dynamic_approval_pathway,
    project_rule_candidate: dict[str, Any] | None = None,
    approval_pathway_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the dynamic property evidence chain without mutating legacy analysis."""
    project_intent = interpret_project_intent(project_goal)
    zoning = zoning_analysis(
        municipality=municipality,
        block=block,
        lot=lot,
        geometry=geometry,
        db=db,
    )

    zoning_promotion = zoning.get("promotion") or {}
    zoning_promotable = zoning_promotion.get("promotable") is True

    zoning_candidate = zoning.get("candidate") or {}
    record = zoning_candidate.get("record") or {}
    zoning_district = record.get("zoning_district")
    documents = _load_dynamic_source_documents(db, municipality) if zoning_district else []

    discovered_project_rule_candidate = project_rule_candidate
    if discovered_project_rule_candidate is None and zoning_district:
        discovered = project_rule_discoverer(
            municipality=municipality,
            zoning_district=zoning_district,
            project_goal=project_goal,
            source_documents=documents,
        )
        if discovered.get("status") == "PROJECT_RULE_EVIDENCE_DISCOVERED":
            discovered_project_rule_candidate = {
                "status": "PROJECT_RULES_CANDIDATE",
                "municipality": municipality,
                "zoning_district": zoning_district,
                "project_goal": project_goal,
                "requirements": discovered.get("requirements", []),
                "source": discovered.get("source", {}),
                "authoritative": discovered.get("source", {}).get("authoritative") is True,
                "legal_control_confirmed": discovered.get("source", {}).get("legal_control_confirmed") is True,
                "discovery": discovered,
            }

    discovered_approval_pathway_candidate = approval_pathway_candidate
    if discovered_approval_pathway_candidate is None and zoning_district:
        discovered_approval_pathway_candidate = approval_pathway_discoverer(
            municipality=municipality,
            zoning_district=zoning_district,
            project_goal=project_goal,
            source_documents=documents,
        )

    if not zoning_promotable:
        project_result = _verify("DYNAMIC_ZONING_NOT_PROMOTABLE")
        approval_result = _verify("DYNAMIC_ZONING_NOT_PROMOTABLE")
    else:
        if discovered_project_rule_candidate is None:
            project_result = _verify("NO_PROJECT_RULE_EVIDENCE")
        else:
            project_result = project_evaluator(discovered_project_rule_candidate)
        approval_result = approval_evaluator(discovered_approval_pathway_candidate)

    return {
        "status": "DYNAMIC_ANALYSIS_COMPLETE",
        "project_intent": project_intent,
        "zoning": zoning,
        "project_rule_candidate": discovered_project_rule_candidate,
        "project_applicability": project_result,
        "approval_pathway_candidate": discovered_approval_pathway_candidate,
        "approval_pathway": approval_result,
        "dynamic_promotable": zoning_promotable,
    }
