"""First-class property evidence/document artifacts for MIDRA Intelligence.

Phase 5.26 contract:
- preserve original source identity and retrieval/version evidence;
- keep zoning-map and tax-map artifacts independent;
- support workspace view/download without changing legal-control decisions;
- expose report eligibility separately from customer report entitlement;
- never guess a tax-map sheet or promote an unverified source.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

_MAP_ROLES = {"zoning_map": "ZONING_MAP", "tax_map": "TAX_MAP"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _artifact_id(*, municipality: str, artifact_type: str, source_url: str, content_hash: str | None) -> str:
    seed = "|".join([municipality.strip().lower(), artifact_type, source_url.strip(), _text(content_hash)])
    return "MEA-" + sha256(seed.encode("utf-8")).hexdigest()[:16].upper()


def build_evidence_artifact(
    *,
    municipality: str,
    source: dict[str, Any],
    block: str | None = None,
    lot: str | None = None,
) -> dict[str, Any] | None:
    """Normalize one already-discovered map source into a preserved artifact.

    This function does not discover, retrieve, classify, or promote a source.
    It only packages evidence already known to MIDRA.
    """
    role = _text(source.get("source_role")).lower()
    artifact_type = _MAP_ROLES.get(role)
    source_url = _text(source.get("source_url") or source.get("url"))
    if artifact_type is None or not source_url.startswith(("http://", "https://")):
        return None

    official = bool(
        source.get("municipal_official_link_verified") is True
        or source.get("authority_verified") is True
        or source.get("authoritative") is True
    )
    content_hash = _text(source.get("content_hash")) or None
    sheet = source.get("tax_map_sheet") or source.get("sheet")

    return {
        "artifact_id": _artifact_id(
            municipality=municipality,
            artifact_type=artifact_type,
            source_url=source_url,
            content_hash=content_hash,
        ),
        "artifact_type": artifact_type,
        "municipality": municipality,
        "block": _text(block) or None,
        "lot": _text(lot) or None,
        "label": _text(source.get("label") or source.get("title")) or artifact_type.replace("_", " ").title(),
        "source_url": source_url,
        "retrieval_url": _text(source.get("retrieval_url")) or None,
        "discovered_from": _text(source.get("discovered_from")) or None,
        "retrieved_at": _text(source.get("retrieved_at")) or None,
        "content_hash": content_hash,
        "content_type": _text(source.get("content_type")) or None,
        "official_source_verified": official,
        "tax_map_sheet": _text(sheet) or None,
        "workspace": {"view_original": True, "download_original": True},
        "report_eligibility": {
            "preliminary": False,
            "complete": official,
            "engineering_internal": True,
        },
        "preservation": {
            "preserve_original": True,
            "snapshot_identity_available": bool(content_hash or source.get("retrieved_at")),
        },
    }


def build_property_evidence_package(
    *, municipality: str, block: str | None, lot: str | None, sources: list[dict[str, Any]]
) -> dict[str, Any]:
    artifacts = []
    seen = set()
    for source in sources or []:
        artifact = build_evidence_artifact(
            municipality=municipality, source=source, block=block, lot=lot
        )
        if artifact is None or artifact["artifact_id"] in seen:
            continue
        seen.add(artifact["artifact_id"])
        artifacts.append(artifact)
    return {
        "status": "EVIDENCE_PACKAGE_READY",
        "municipality": municipality,
        "block": _text(block),
        "lot": _text(lot),
        "artifacts": artifacts,
    }
