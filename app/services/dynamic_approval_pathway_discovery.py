"""Conservative discovery of approval-pathway evidence from retrieved municipal sources.

This module extracts only explicit pathway/review-body language from source content.
It never upgrades source authority or legal control. Promotion remains exclusively
with evaluate_dynamic_approval_pathway.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.project_intent_normalization import project_intent_search_terms


_PROJECT_TERMS = {
    "pool": ("swimming pool", "swimming pools", "private swimming pool", "pool"),
    "swimming_pool": ("swimming pool", "swimming pools", "private swimming pool", "pool"),
    "addition": ("addition", "building addition"),
    "garage": ("garage", "detached garage"),
    "shed": ("shed", "storage shed"),
    "deck": ("deck", "patio"),
    "driveway": ("driveway",),
    "adu": ("accessory dwelling unit", "accessory dwelling", "adu"),
    "new_home": ("new home", "single family dwelling", "single-family dwelling"),
    "subdivision": ("subdivision", "subdivide"),
    "commercial": ("commercial",),
}

_PATHWAYS = (
    ("SITE_PLAN_APPROVAL", ("site plan approval", "site-plan approval")),
    ("SUBDIVISION_APPROVAL", ("subdivision approval",)),
    ("CONDITIONAL_USE_APPROVAL", ("conditional use approval",)),
    ("ZONING_PERMIT", ("zoning permit", "zoning approval")),
    ("VARIANCE", ("variance approval", "variance")),
)

_REVIEWING_BODIES = (
    ("PLANNING_BOARD", ("planning board",)),
    ("ZONING_BOARD_OF_ADJUSTMENT", ("zoning board of adjustment", "board of adjustment")),
    ("LAND_USE_BOARD", ("land use board",)),
    ("ZONING_OFFICER", ("zoning officer",)),
)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _clean_text(content: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", content or "", flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _project_terms(project_goal: str) -> tuple[str, ...]:
    shared = project_intent_search_terms(project_goal)
    if shared:
        return shared
    key = _normalize(project_goal).replace("-", "_")
    return _PROJECT_TERMS.get(key, (_normalize(project_goal),))


def _source_from_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: document.get(key)
        for key in (
            "source_url",
            "label",
            "source_role",
            "authority_tier",
            "evidence_status",
            "discovery_source",
            "source_type",
            "authoritative",
            "legal_control_confirmed",
        )
        if document.get(key) is not None
    }


def extract_dynamic_approval_pathway_candidate(
    *,
    municipality: str,
    zoning_district: str,
    project_goal: str,
    source_document: dict[str, Any],
) -> dict[str, Any]:
    """Extract explicit approval evidence near the requested project context."""
    content = source_document.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"status": "VERIFY", "reason": "SOURCE_CONTENT_UNAVAILABLE"}

    text = _clean_text(content)
    lowered = text.lower()
    terms = tuple(term for term in _project_terms(project_goal) if term)
    if not terms:
        return {"status": "VERIFY", "reason": "PROJECT_GOAL_MISSING"}

    project_hits = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    if not project_hits:
        return {"status": "VERIFY", "reason": "PROJECT_CONTEXT_NOT_FOUND"}

    pathway_match: tuple[str, str, int] | None = None
    for pathway, phrases in _PATHWAYS:
        for phrase in phrases:
            start = 0
            while True:
                pos = lowered.find(phrase, start)
                if pos < 0:
                    break
                # Require pathway language reasonably near the requested project.
                if min(abs(pos - hit) for hit in project_hits) <= 2200:
                    pathway_match = (pathway, phrase, pos)
                    break
                start = pos + 1
            if pathway_match:
                break
        if pathway_match:
            break

    if not pathway_match:
        return {"status": "VERIFY", "reason": "APPROVAL_PATHWAY_NOT_EXPLICIT"}

    pathway, phrase, pos = pathway_match
    start = max(0, pos - 1000)
    end = min(len(text), pos + 1800)
    excerpt = text[start:end].strip()
    excerpt_lower = excerpt.lower()

    reviewing_bodies = [
        code
        for code, phrases in _REVIEWING_BODIES
        if any(phrase in excerpt_lower for phrase in phrases)
    ]

    # Explicit approval language is required; reviewing body may legitimately be absent.
    requirement = {
        "requirement": f"{project_goal} approval-pathway evidence",
        "evidence_type": "MUNICIPAL_APPROVAL_TEXT",
        "zoning_district": zoning_district,
        "project_goal": project_goal,
        "primary_pathway": pathway,
        "matched_phrase": phrase,
        "excerpt": excerpt,
        "source_url": source_document.get("source_url") or source_document.get("url"),
        "source_label": source_document.get("label", ""),
    }

    source = _source_from_document(source_document)
    return {
        "status": "APPROVAL_PATHWAY_CANDIDATE",
        "municipality": municipality,
        "zoning_district": zoning_district,
        "project_goal": project_goal,
        "primary_pathway": pathway,
        "possible_alternative": None,
        "reviewing_bodies": reviewing_bodies,
        "requirements": [requirement],
        "source": source,
        "authoritative": source.get("authoritative") is True,
        "legal_control_confirmed": source.get("legal_control_confirmed") is True,
        "evidence_status": "CANDIDATE_ONLY",
    }


def discover_dynamic_approval_pathway_candidate(
    *,
    municipality: str,
    zoning_district: str,
    project_goal: str,
    source_documents: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return the first explicit approval-pathway candidate, otherwise None."""
    for document in source_documents or []:
        result = extract_dynamic_approval_pathway_candidate(
            municipality=municipality,
            zoning_district=zoning_district,
            project_goal=project_goal,
            source_document=document,
        )
        if result.get("status") == "APPROVAL_PATHWAY_CANDIDATE":
            return result
    return None
