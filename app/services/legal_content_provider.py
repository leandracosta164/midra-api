"""Provider-agnostic acquisition of verified municipal legal content.

This module selects a legal-content provider only from an explicit source URL or
a provider URL actually observed during retrieval.  It does not discover or
synthesize provider URLs and it never grants legal-control status.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.core.settings import settings
from app.services.ecode360_api_retrieval import retrieve_ecode_zoning_content


@dataclass(frozen=True)
class LegalContentRequest:
    source_url: str
    retrieval_meta: dict[str, Any]


class LegalContentProvider(Protocol):
    name: str

    def match(self, request: LegalContentRequest) -> str | None:
        """Return the explicit representation this provider can handle."""

    def acquire(
        self,
        client: Any,
        *,
        request: LegalContentRequest,
        representation_url: str,
    ) -> tuple[Any | None, dict[str, Any]]:
        """Acquire legal content without changing source identity or legal status."""


class ECode360Provider:
    name = "ecode360"

    def __init__(
        self,
        *,
        retriever: Callable[..., tuple[Any | None, dict[str, Any]]] = retrieve_ecode_zoning_content,
    ) -> None:
        self._retriever = retriever

    def match(self, request: LegalContentRequest) -> str | None:
        candidates = (
            str(request.source_url or "").strip(),
            str((request.retrieval_meta or {}).get("final_url") or "").strip(),
        )
        return next(
            (url for url in candidates if "ecode360.com/" in url.lower()),
            None,
        )

    def acquire(
        self,
        client: Any,
        *,
        request: LegalContentRequest,
        representation_url: str,
    ) -> tuple[Any | None, dict[str, Any]]:
        response, provider_meta = self._retriever(
            client,
            source_url=representation_url,
            api_key=settings.ECODE360_API_KEY,
            api_secret=settings.ECODE360_API_SECRET,
        )
        return response, {
            "provider": self.name,
            "provider_representation_url": representation_url,
            "provider_result": provider_meta,
            **(provider_meta if response is not None else {}),
        }


def default_legal_content_providers() -> tuple[LegalContentProvider, ...]:
    """Registered legal-content providers, ordered by explicit matching only."""
    return (ECode360Provider(),)


def acquire_legal_content(
    client: Any,
    *,
    source_url: str,
    retrieval_meta: dict[str, Any] | None,
    providers: tuple[LegalContentProvider, ...] | None = None,
) -> tuple[Any | None, dict[str, Any]]:
    """Acquire content through the first provider that explicitly matches.

    If no provider matches, the original retrieval metadata is returned unchanged.
    Provider diagnostics are preserved even when acquisition is unavailable.
    """
    base_meta = dict(retrieval_meta or {})
    request = LegalContentRequest(source_url=source_url, retrieval_meta=base_meta)

    for provider in providers or default_legal_content_providers():
        representation_url = provider.match(request)
        if not representation_url:
            continue
        response, provider_meta = provider.acquire(
            client,
            request=request,
            representation_url=representation_url,
        )
        combined = {
            **base_meta,
            "legal_content_provider": provider.name,
            **provider_meta,
        }
        return response, combined

    return None, base_meta
