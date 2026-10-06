"""Orchestration bridge for dynamic zoning evidence providers.

This layer connects the source catalog/cache to future concrete zoning
providers without changing the legacy zoning-resolution behavior. A provider
must explicitly understand a source and return validated parcel-specific
evidence; otherwise the pipeline reports no dynamic result.
"""
from __future__ import annotations

from typing import Any, Iterable

from app.services.source_history import get_cached_source_content
from app.services.zoning_evidence_provider import ZoningEvidenceProvider
from app.services.zoning_source_selector import select_zoning_source_candidates


def collect_dynamic_zoning_evidence(
    *,
    municipality: str,
    block: str,
    lot: str,
    db: Any,
    providers: Iterable[ZoningEvidenceProvider] = (),
) -> dict[str, Any]:
    """Try registered providers against cached catalog source representations.

    The function is intentionally non-authoritative by default: only a
    provider that returns a concrete evidence record can produce a result.
    Missing cache content, unsupported providers, or insufficient evidence
    are reported as VERIFY-compatible diagnostics rather than inferred zoning.
    """
    candidates = select_zoning_source_candidates(municipality=municipality, db=db)
    attempted: list[dict[str, Any]] = []

    provider_list = list(providers)
    for source in candidates:
        content_hash = source.get("current_content_hash")
        if not content_hash:
            attempted.append({**source, "status": "CONTENT_NOT_CACHED"})
            continue

        content = get_cached_source_content(
            db,
            source_url=source["source_url"],
            content_hash=content_hash,
        )
        if content is None:
            attempted.append({**source, "status": "CONTENT_NOT_CACHED"})
            continue

        supported = False
        for provider in provider_list:
            if not provider.supports(source):
                continue
            supported = True
            record = provider.extract(
                municipality=municipality,
                block=block,
                lot=lot,
                source=source,
                content=content,
            )
            if record is not None:
                return {
                    "status": "ZONING_RESOLVED",
                    "record": record.as_adapter_input(),
                    "source_candidates": candidates,
                    "attempted": attempted + [{**source, "status": "EVIDENCE_EXTRACTED"}],
                }

        attempted.append(
            {
                **source,
                "status": "PROVIDER_UNSUPPORTED" if not supported else "EVIDENCE_INSUFFICIENT",
            }
        )

    return {
        "status": "ZONING_NOT_RESOLVED",
        "source_candidates": candidates,
        "attempted": attempted,
        "reason": "No registered provider produced parcel-specific zoning evidence from cached source content.",
    }
