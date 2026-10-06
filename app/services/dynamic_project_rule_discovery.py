"""Evidence-driven discovery of project rules from retrieved municipal sources.

This service does not maintain municipality-specific rule tables. It extracts
candidate evidence from already retrieved source representations and leaves
legal-control/promotion decisions to the existing dynamic applicability layer.
"""
from __future__ import annotations

import re
from typing import Any

from app.services.project_intent_normalization import project_intent_search_terms

PROJECT_TERMS = {
    "pool": ("swimming pool", "swimming pools", "private swimming pool", "pool"),
    "swimming_pool": ("swimming pool", "swimming pools", "private swimming pool", "pool"),
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _project_terms(project_goal: str) -> tuple[str, ...]:
    shared = project_intent_search_terms(project_goal)
    if shared:
        return shared
    key = _normalize(project_goal).replace("-", "_")
    return PROJECT_TERMS.get(key, (key,))


def _clean_text(content: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", content or "", flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _district_pattern(zoning_district: str) -> re.Pattern[str]:
    escaped = re.escape(_normalize(zoning_district))
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.I)


def _district_aliases(zoning_district: str) -> tuple[str, ...]:
    value = _normalize(zoning_district)
    aliases = [value]
    if value.startswith("r-m("):
        aliases.append("r-m")
    return tuple(dict.fromkeys(aliases))


def _referenced_districts(text: str, anchor_excerpt: str) -> list[str]:
    patterns = (
        r"all\s+accessory\s+uses\s+as\s+permitted\s+in\s+the\s+([A-Za-z0-9\-()]+)\s+zone",
        r"all\s+conditional\s+uses\s+as\s+specified\s+in\s+the\s+([A-Za-z0-9\-()]+)\s+zone",
        r"uses\s+as\s+permitted\s+in\s+the\s+([A-Za-z0-9\-()]+)\s+zone",
        r"as\s+permitted\s+in\s+the\s+([A-Za-z0-9\-()]+)\s+zone",
    )
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, anchor_excerpt, flags=re.I):
            district = match.group(1).strip()
            if district.lower() not in {x.lower() for x in found}:
                found.append(district)
    return found


def _district_reference_excerpt(text: str, district: str) -> str | None:
    aliases = _district_aliases(district)
    for alias in aliases:
        matches = list(re.finditer(
            rf"(?<![a-z0-9]){re.escape(alias)}(?:\s+residential)?(?:\s+zone)?(?=\s|[.,:;)]|$)",
            text,
            re.I,
        ))
        for match in reversed(matches):
            header_start = text.rfind("§", 0, match.start())
            if header_start >= 0 and match.start() - header_start < 80:
                start = header_start
                next_section = re.search(r"§\s*\d+[A-Za-z0-9.-]*", text[match.end():])
                end = match.end() + next_section.start() if next_section else min(len(text), match.start() + 5000)
                return text[start:end]
        if matches:
            match = matches[-1]
            start = max(0, match.start() - 250)
            return text[start:min(len(text), match.start() + 5000)]
    return None


def extract_project_rule_evidence(
    *,
    municipality: str,
    zoning_district: str,
    project_goal: str,
    source_document: dict[str, Any],
) -> dict[str, Any]:
    """Extract a conservative project-rule evidence candidate from one source."""
    content = source_document.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"status": "VERIFY", "reason": "SOURCE_CONTENT_UNAVAILABLE"}

    text = _clean_text(content)
    district_match = _district_pattern(zoning_district).search(text)
    if not district_match:
        return {"status": "VERIFY", "reason": "ZONING_DISTRICT_NOT_FOUND"}

    lowered = text.lower()

    section_start = district_match.start()
    next_section = re.search(r"§\s*\d+[A-Za-z0-9.-]*", text[district_match.end():])
    section_end = district_match.end() + next_section.start() if next_section else len(text)
    district_section = text[section_start:section_end].strip()
    section_lower = district_section.lower()

    term = next((candidate for candidate in _project_terms(project_goal) if candidate in section_lower), None)
    permission_signal = False
    excerpt = district_section[:3600].strip()

    if term:
        permission_signal = any(
            token in _normalize(district_section)
            for token in (
                "permitted accessory", "permitted use", "permitted uses",
                "shall be permitted", "accessory use", "accessory uses",
                "conditional use", "conditional uses", "allowed"
            )
        )

    if not permission_signal:
        referenced = _referenced_districts(text, district_section)
        for referenced_district in referenced:
            reference_excerpt = _district_reference_excerpt(text, referenced_district)
            if not reference_excerpt:
                continue
            reference_lower = reference_excerpt.lower()
            reference_term = next((candidate for candidate in _project_terms(project_goal) if candidate in reference_lower), None)
            reference_context = _normalize(reference_excerpt)
            reference_permission = reference_term and any(
                token in reference_context
                for token in (
                    "permitted accessory", "permitted use", "permitted uses",
                    "shall be permitted", "accessory use", "accessory uses", "allowed"
                )
            )
            if reference_permission:
                excerpt = excerpt + "\n[Referenced district evidence: " + reference_excerpt.strip() + "]"
                permission_signal = True
                break

    if not term and not permission_signal:
        return {"status": "VERIFY", "reason": "PROJECT_TERM_NOT_FOUND"}
    if not permission_signal:
        return {"status": "VERIFY", "reason": "PERMISSION_CONTEXT_NOT_CONFIRMED"}

    requirement = {
        "requirement": f"{project_goal} rule evidence",
        "evidence_type": "MUNICIPAL_ORDINANCE_TEXT",
        "zoning_district": zoning_district,
        "project_goal": project_goal,
        "excerpt": excerpt,
        "source_url": source_document.get("source_url") or source_document.get("url"),
        "source_label": source_document.get("label", ""),
    }

    source = {
        key: source_document.get(key)
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
        if source_document.get(key) is not None
    }

    return {
        "status": "PROJECT_RULE_EVIDENCE_DISCOVERED",
        "municipality": municipality,
        "zoning_district": zoning_district,
        "project_goal": project_goal,
        "requirements": [requirement],
        "source": source,
        "evidence_status": "CANDIDATE_ONLY",
    }


def discover_dynamic_project_rule_candidate(
    *,
    municipality: str,
    zoning_district: str,
    project_goal: str,
    source_documents: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Search retrieved municipal source documents for explicit project-rule evidence."""
    for document in source_documents or []:
        result = extract_project_rule_evidence(
            municipality=municipality,
            zoning_district=zoning_district,
            project_goal=project_goal,
            source_document=document,
        )
        if result.get("status") == "PROJECT_RULE_EVIDENCE_DISCOVERED":
            return result

    return {
        "status": "VERIFY",
        "reason": "NO_PROJECT_RULE_EVIDENCE",
        "municipality": municipality,
        "zoning_district": zoning_district,
        "project_goal": project_goal,
    }
