"""Evidence that a municipality explicitly publishes a concrete zoning representation.

This layer is intentionally separate from legal control.  It can establish that an
exact map/viewer/document is presented by an official municipal page as zoning
information, but it cannot establish that the digital representation is the adopted
legal-control instrument.
"""
from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

_ITEM_ID_RE = re.compile(r"^[0-9a-f]{32}$", re.I)
_ZONING_CONTEXT_RE = re.compile(
    r"\b(?:"
    r"zoning(?:\s+(?:map|maps|viewer|information|district|districts|ordinance|ordinances))?"
    r"|interactive\s+zoning"
    r"|official\s+zoning\s+map"
    r"|land\s+use\s+map"
    r")\b",
    re.I,
)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>", re.I | re.S)
_WHITESPACE_RE = re.compile(r"\s+")


def _visible_text(value: str) -> str:
    # Zoning context is a human-facing publication signal.  Search rendered-ish
    # page text rather than raw HTML/JS so an unrelated script variable named
    # ``zoning`` cannot promote a source.
    without_scripts = _SCRIPT_STYLE_RE.sub(" ", value)
    without_tags = _TAG_RE.sub(" ", without_scripts)
    return _WHITESPACE_RE.sub(" ", html.unescape(without_tags)).strip()


def _host(url: object) -> str:
    try:
        return urlparse(str(url or "").strip()).netloc.lower()
    except ValueError:
        return ""


def _municipality_key(value: object) -> str:
    tokens = [
        token for token in str(value or "").lower().replace("_", " ").split()
        if token not in {"city", "township", "twp", "borough", "boro", "town", "village", "of"}
    ]
    return "".join(ch for ch in "".join(tokens) if ch.isalnum())


def _official_municipal_host(url: object, municipality: object) -> bool:
    host = _host(url)
    if not host:
        return False
    # ``nj.gov`` alone is a state-government signal, not proof that the page is
    # controlled by the municipality. Municipal ``.nj.us`` hosts are accepted;
    # other domains must carry the municipality identity in the hostname.
    if host.endswith(".nj.us"):
        return True
    key = _municipality_key(municipality)
    host_key = "".join(ch for ch in host if ch.isalnum())
    return bool(key and key in host_key)


def _normalized_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"




def _decoded_reference_text(value: str, *, max_rounds: int = 3) -> str:
    """Return raw HTML plus bounded URL-decoded forms for redirect-wrapped links.

    Municipal CMS/security gateways commonly wrap an external target in a query
    parameter (for example ``?u=https%3A%2F%2F...``).  Decoding is bounded and
    used only for exact target matching; it does not grant authority to the
    wrapper host or relax the official-page/zoning-context requirements.
    """
    variants = [value]
    current = value
    for _ in range(max_rounds):
        decoded = unquote(html.unescape(current))
        if decoded == current:
            break
        variants.append(decoded)
        current = decoded
    return "\n".join(variants)

def _arcgis_ids(source: dict[str, Any]) -> set[str]:
    values = {source.get("arcgis_item_id"), source.get("item_id"), source.get("webmap_id")}
    for key in ("source_url", "url"):
        raw = str(source.get(key) or "").strip()
        if not raw:
            continue
        try:
            parsed = urlparse(raw)
            values.update(parse_qs(parsed.query).get("appid", []))
            values.update(parse_qs(parsed.query).get("id", []))
        except ValueError:
            pass
    return {str(v).strip().lower() for v in values if v and _ITEM_ID_RE.fullmatch(str(v).strip())}


def evaluate_official_zoning_representation(
    *,
    municipality: str,
    official_page_url: str,
    official_page_content: str | bytes | None,
    target_source: dict[str, Any] | None,
) -> dict[str, Any]:
    """Verify that an official municipal page explicitly presents an exact target as zoning information.

    Positive evidence establishes official-publication authority for the target. It
    deliberately leaves ``legal_control_confirmed`` false.
    """
    target = dict(target_source or {})
    if not _official_municipal_host(official_page_url, municipality):
        return {
            "status": "OFFICIAL_REPRESENTATION_NOT_VERIFIED",
            "authority_verified": False,
            "legal_control_confirmed": False,
            "reason": "OFFICIAL_MUNICIPAL_PAGE_NOT_VERIFIED",
            "signals": [],
        }

    if isinstance(official_page_content, bytes):
        text = official_page_content.decode("utf-8", "ignore")
    else:
        text = str(official_page_content or "")
    if not text.strip():
        return {
            "status": "OFFICIAL_REPRESENTATION_NOT_VERIFIED",
            "authority_verified": False,
            "legal_control_confirmed": False,
            "reason": "OFFICIAL_PAGE_CONTENT_EMPTY",
            "signals": [],
        }

    visible_text = _visible_text(text)
    if not _ZONING_CONTEXT_RE.search(visible_text):
        return {
            "status": "OFFICIAL_REPRESENTATION_NOT_VERIFIED",
            "authority_verified": False,
            "legal_control_confirmed": False,
            "reason": "ZONING_CONTEXT_NOT_ESTABLISHED",
            "signals": [],
        }

    lowered = text.lower()
    decoded_references = _decoded_reference_text(text).lower()
    signals = ["OFFICIAL_MUNICIPAL_PAGE", "EXPLICIT_ZONING_CONTEXT"]
    matched_reference = None

    target_urls = {
        _normalized_url(target.get("source_url")),
        _normalized_url(target.get("url")),
    } - {""}
    for url in sorted(target_urls):
        if url.lower() in lowered:
            signals.append("EXACT_TARGET_URL_REFERENCE")
            matched_reference = url
            break
        if url.lower() in decoded_references:
            signals.extend(["REDIRECT_WRAPPED_TARGET_REFERENCE", "EXACT_TARGET_URL_REFERENCE"])
            matched_reference = url
            break

    if matched_reference is None:
        for item_id in sorted(_arcgis_ids(target)):
            if item_id in lowered or item_id in decoded_references:
                signals.append("EXACT_ARCGIS_ITEM_ID_REFERENCE")
                if item_id not in lowered:
                    signals.append("REDIRECT_WRAPPED_TARGET_REFERENCE")
                matched_reference = item_id
                break

    if matched_reference is None:
        return {
            "status": "OFFICIAL_REPRESENTATION_NOT_VERIFIED",
            "authority_verified": False,
            "legal_control_confirmed": False,
            "reason": "TARGET_NOT_EXPLICITLY_LINKED_FROM_OFFICIAL_ZONING_CONTEXT",
            "signals": signals,
        }

    return {
        "status": "OFFICIAL_ZONING_REPRESENTATION_VERIFIED",
        "authority_verified": True,
        "authoritative": True,
        "legal_control_confirmed": False,
        "reason": "MUNICIPAL_OFFICIAL_PAGE_EXPLICITLY_PUBLISHES_TARGET_AS_ZONING_INFORMATION",
        "official_page_url": official_page_url,
        "target_source": target,
        "matched_reference": matched_reference,
        "signals": signals,
    }
