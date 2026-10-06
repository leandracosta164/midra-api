"""Conservative natural-language project intent interpretation for MIDRA Property.

The interpreter improves source search terms without creating zoning, permitting,
or approval conclusions. Unknown/custom text remains custom and is never treated
as a regulatory determination.
"""
from __future__ import annotations

import re
from typing import Any


_INTENTS: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("pool", "Pool", ("pool", "swimming pool", "inground pool", "in-ground pool"), ("swimming pool", "swimming pools", "private swimming pool", "pool")),
    ("addition", "Addition", ("addition", "home addition", "building addition"), ("addition", "building addition", "home addition")),
    ("garage", "Garage", ("garage", "detached garage"), ("garage", "detached garage", "accessory garage")),
    ("shed", "Shed", ("shed", "storage shed"), ("shed", "storage shed", "accessory structure")),
    ("deck", "Deck / Patio", ("deck", "patio"), ("deck", "patio", "terrace")),
    ("driveway", "Driveway", ("driveway", "curb cut"), ("driveway", "curb cut", "driveway access")),
    ("adu", "Accessory Dwelling Unit", ("adu", "accessory dwelling", "accessory dwelling unit"), ("accessory dwelling unit", "accessory dwelling", "adu")),
    ("new_home", "New Home", ("new home", "new house", "single family home", "single-family home"), ("single family dwelling", "single-family dwelling", "new home", "dwelling")),
    ("subdivision", "Subdivision", ("subdivision", "subdivide", "lot split"), ("subdivision", "subdivide", "minor subdivision", "major subdivision", "lot split")),
    ("mixed_use", "Mixed-Use Development", ("mixed use", "mixed-use", "mixed use building", "mixed-use building"), ("mixed use", "mixed-use", "mixed use development", "mixed-use development")),
    ("multifamily", "Multifamily Development", ("multifamily", "multi-family", "apartment", "apartments", "condominium", "condominiums"), ("multifamily", "multi-family", "apartment", "apartments", "dwelling units")),
    ("warehouse", "Warehouse / Distribution", ("warehouse", "distribution center", "distribution facility"), ("warehouse", "distribution center", "distribution facility")),
    ("industrial", "Industrial Development", ("industrial", "manufacturing", "factory"), ("industrial", "manufacturing", "factory", "industrial use")),
    ("retail", "Retail", ("retail", "store", "shopping center"), ("retail", "retail use", "store", "shopping center")),
    ("restaurant", "Restaurant / Food Service", ("restaurant", "cafe", "coffee shop", "food service"), ("restaurant", "food service", "cafe")),
    ("office", "Office", ("office", "medical office", "professional office"), ("office", "professional office", "medical office")),
    ("solar", "Solar Energy", ("solar", "solar array", "solar panels", "photovoltaic"), ("solar", "solar array", "solar energy system", "photovoltaic")),
    ("ev_charging", "EV Charging", ("ev charging", "electric vehicle charging", "charging station"), ("electric vehicle charging", "ev charging", "charging station")),
    ("commercial", "Commercial Development", ("commercial", "commercial development"), ("commercial", "commercial use", "commercial development")),
    ("redevelopment", "Redevelopment", ("redevelopment", "redevelop", "adaptive reuse"), ("redevelopment", "redevelop", "adaptive reuse")),
    ("change_of_use", "Change of Use", ("change of use", "change-of-use", "convert use", "conversion"), ("change of use", "change-of-use", "conversion")),
)

_STOPWORDS = {
    "a","an","and","at","build","building","construct","construction","develop","development",
    "for","from","i","in","install","into","land","lot","my","new","of","on","or","plan",
    "project","property","proposed","site","the","to","want","with","would",
}


def _normalize(value: Any) -> str:
    text=str(value or "").lower().replace("_"," ").replace("/"," ")
    text=re.sub(r"[^a-z0-9+.-]+"," ",text)
    return re.sub(r"\s+"," ",text).strip()


def _unique(items: list[str]) -> list[str]:
    out=[]; seen=set()
    for item in items:
        value=_normalize(item)
        if value and value not in seen:
            seen.add(value); out.append(value)
    return out


def _custom_terms(normalized: str) -> list[str]:
    tokens=[t for t in normalized.split() if len(t)>=3 and t not in _STOPWORDS and not t.isdigit()]
    terms=[]
    if normalized and normalized not in {"other","general property research","general research"}:
        terms.append(normalized)
    for size in (3,2):
        for i in range(0,max(0,len(tokens)-size+1)):
            terms.append(" ".join(tokens[i:i+size]))
    terms.extend(tokens)
    return _unique(terms)[:12]


def interpret_project_intent(project_goal: str) -> dict[str, Any]:
    raw=str(project_goal or "").strip()
    normalized=_normalize(raw)
    if not normalized or normalized in {"other","general property research","general research","property research"}:
        return {
            "status":"GENERAL_PROPERTY_RESEARCH",
            "raw_goal":raw or "other",
            "primary_intent":"general_research",
            "intent_types":[],
            "display_label":"General property research",
            "search_terms":[],
            "interpretation_basis":"NO_SPECIFIC_PROJECT_ASSERTED",
        }

    matches=[]
    search=[]
    labels=[]
    for code,label,signals,terms in _INTENTS:
        if any(_normalize(signal) in normalized for signal in signals):
            matches.append(code); labels.append(label); search.extend(terms)

    if matches:
        return {
            "status":"PROJECT_INTENT_INTERPRETED",
            "raw_goal":raw,
            "primary_intent":matches[0],
            "intent_types":matches,
            "display_label":" + ".join(labels[:3]),
            "search_terms":_unique(search),
            "interpretation_basis":"EXPLICIT_PROJECT_LANGUAGE",
        }

    custom=_custom_terms(normalized)
    return {
        "status":"CUSTOM_PROJECT_INTENT",
        "raw_goal":raw,
        "primary_intent":"custom",
        "intent_types":["custom"],
        "display_label":raw or "Custom project",
        "search_terms":custom,
        "interpretation_basis":"CUSTOM_TEXT_SEARCH_TERMS_ONLY",
    }


def project_intent_search_terms(project_goal: str) -> tuple[str, ...]:
    return tuple(interpret_project_intent(project_goal).get("search_terms") or ())
