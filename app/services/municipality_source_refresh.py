"""Retrieve and version sources discovered from the NJ DCA directory."""

from __future__ import annotations

from typing import Any
from datetime import datetime

import httpx

from app.services.municipality_source_discovery import (
    discover_municipality_sources,
)
from app.services.source_history import persist_source_snapshot
from app.services.source_catalog import upsert_source_catalog_entry
from app.services.source_classification import classify_discovered_source
from app.services.source_versioning import build_snapshot
from app.services.municipal_source_link_following import (
    discover_ordinance_links,
    discover_explicit_document_links,
)
from app.services.municipal_source_retrieval import retrieve_source
from app.services.municipal_document_discovery import discover_explicit_municipal_documents
from app.services.municipal_tax_map_discovery import discover_explicit_tax_map_links
from app.services.municipal_zoning_page_discovery import (
    discover_zoning_page_links,
    municipal_site_root,
)
from app.services.legal_content_provider import acquire_legal_content
from app.core.settings import settings

REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
USER_AGENT = "MIDRA-Engineering-Property-Intelligence/1.0 (municipal-source-refresh)"


def _try_legal_content_acquisition(
    *,
    client: Any,
    source_url: str,
    retrieval_meta: dict[str, Any],
) -> tuple[Any | None, dict[str, Any]]:
    """Try a registered provider using only explicit/observed source identity."""
    response, combined_meta = acquire_legal_content(
        client,
        source_url=source_url,
        retrieval_meta=retrieval_meta,
    )
    # Preserve the legacy eCode diagnostic key while callers/logs transition to
    # provider-neutral metadata.  This is compatibility metadata, not routing.
    provider_result = combined_meta.get("provider_result")
    if combined_meta.get("legal_content_provider") == "ecode360" and isinstance(provider_result, dict):
        combined_meta = {**combined_meta, "ecode_api": provider_result}
    return response, combined_meta

def _cache_explicit_legal_links_from_official_page(
    *,
    client: Any,
    canonical_municipality: str,
    page_url: str,
    page_content: bytes,
    page_label: str,
    results: list[dict[str, Any]],
) -> None:
    """Cache legal/code links explicitly published by an official municipal page.

    This helper is deliberately bounded to the supplied page. It does not crawl,
    search, synthesize URLs, or grant legal-control status. For eCode360 links the
    normal public retrieval is attempted first; the already-supported authenticated
    API adapter remains the only fallback when credentials are configured.
    """
    # Merge the existing bounded legal-link and explicit-document discovery
    # primitives.  This matters when an official codifier is inaccessible but
    # the same first-party page also publishes an ordinance/code document.
    # Discovery remains one-page/one-hop and does not promote the document.
    explicit_links = discover_ordinance_links(page_url=page_url, content=page_content)
    seen_urls = {item["url"] for item in explicit_links}
    for document in discover_explicit_municipal_documents(
        page_url=page_url, content=page_content
    ):
        if document["url"] not in seen_urls:
            explicit_links.append(document)
            seen_urls.add(document["url"])
    for document in discover_explicit_document_links(
        page_url=page_url, content=page_content
    ):
        if document["url"] not in seen_urls:
            explicit_links.append(document)
            seen_urls.add(document["url"])

    for linked in explicit_links:
        linked_url = linked["url"]
        linked_label = f"Linked ordinance source: {linked['label']}"
        linked_source = {
            "source_type": "linked_municipal_ordinance",
            "discovered_from": page_url,
            "discovery_label": page_label,
            "municipal_official_link_verified": True,
            "municipal_official_page_url": page_url,
        }
        linked_classification = classify_discovered_source(
            linked_label,
            linked_url,
            {**linked_source, "municipality": canonical_municipality},
        )
        upsert_source_catalog_entry(
            municipality=canonical_municipality,
            label=linked_label,
            source_url=linked_url,
            classification=linked_classification,
            source=linked_source,
        )
        try:
            linked_response, linked_retrieval_meta = retrieve_source(
                client, linked_url, referer=page_url
            )
            if linked_response is None:
                linked_response, linked_retrieval_meta = _try_legal_content_acquisition(
                    client=client,
                    source_url=linked_url,
                    retrieval_meta=linked_retrieval_meta,
                )

            if linked_response is None:
                results.append({
                    "label": linked_label,
                    "url": linked_url,
                    **linked_retrieval_meta,
                    "status": "RETRIEVAL_FAILED",
                    "changed": False,
                    "discovered_from": page_url,
                    "municipal_official_link_verified": True,
                })
                continue

            linked_metadata = {
                "label": linked_label,
                "url": str(linked_response.url),
                **linked_classification,
                "status_code": linked_response.status_code,
                "content_type": linked_response.headers.get("content-type", ""),
                "etag": linked_response.headers.get("etag"),
                "last_modified": linked_response.headers.get("last-modified"),
                **linked_retrieval_meta,
                "discovered_from": page_url,
                "municipal_official_link_verified": True,
                "municipal_official_page_url": page_url,
            }
            linked_snapshot = build_snapshot(
                url=str(linked_response.url),
                content=linked_response.content,
                metadata=linked_metadata,
            )
            linked_change = persist_source_snapshot(
                snapshot=linked_snapshot,
                municipality=canonical_municipality,
                source_type=linked_source["source_type"],
                description=f"Explicit ordinance link from official municipal page: {linked['label']}",
                authoritative=False,
            )
            upsert_source_catalog_entry(
                municipality=canonical_municipality,
                label=linked_label,
                source_url=linked_url,
                classification=linked_classification,
                source=linked_source,
                retrieved_at=linked_snapshot.retrieved_at and datetime.fromisoformat(linked_snapshot.retrieved_at),
                content_hash=linked_snapshot.content_hash,
                current_status=linked_change.status,
                retrieval_url=str(linked_response.url),
            )
            linked_metadata.update({
                "status": "RETRIEVED",
                "change_status": linked_change.status,
                "changed": linked_change.changed,
                "retrieved_at": linked_snapshot.retrieved_at,
                "content_hash": linked_snapshot.content_hash,
                "byte_size": linked_snapshot.byte_size,
            })
            results.append(linked_metadata)
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            results.append({
                "label": linked_label,
                "url": linked_url,
                "status": "RETRIEVAL_UNAVAILABLE",
                "changed": False,
                "error_type": exc.__class__.__name__,
                "discovered_from": page_url,
                "municipal_official_link_verified": True,
            })



def _cache_explicit_tax_map_links_from_official_page(
    *,
    client: Any,
    canonical_municipality: str,
    page_url: str,
    page_content: bytes,
    page_label: str,
    results: list[dict[str, Any]],
) -> None:
    """Catalog/retrieve tax maps explicitly linked by a verified municipal page.

    Discovery is one-page/one-hop.  A linked map is recorded as officially
    linked, but is not made legally controlling and no tax-map sheet is inferred.
    """
    for linked in discover_explicit_tax_map_links(page_url=page_url, content=page_content):
        linked_url = str(linked["url"])
        sheet = linked.get("tax_map_sheet")
        linked_label = (
            f"Municipal tax map sheet {sheet}: {linked['label']}"
            if sheet
            else f"Municipal tax map: {linked['label']}"
        )
        linked_source = {
            "source_type": "municipal_tax_map_sheet" if sheet else "municipal_tax_map",
            "source_role": "tax_map",
            "tax_map_sheet": sheet,
            "discovered_from": page_url,
            "discovery_label": page_label,
            "municipal_official_link_verified": True,
            "municipal_official_page_url": page_url,
        }
        linked_classification = classify_discovered_source(
            linked_label,
            linked_url,
            {**linked_source, "municipality": canonical_municipality},
        )
        upsert_source_catalog_entry(
            municipality=canonical_municipality,
            label=linked_label,
            source_url=linked_url,
            classification=linked_classification,
            source=linked_source,
        )

        try:
            linked_response, linked_retrieval_meta = retrieve_source(
                client, linked_url, referer=page_url
            )
            if linked_response is None:
                results.append({
                    "label": linked_label,
                    "url": linked_url,
                    **linked_retrieval_meta,
                    **linked_source,
                    "status": "RETRIEVAL_FAILED",
                    "changed": False,
                })
                continue

            linked_metadata = {
                "label": linked_label,
                "url": str(linked_response.url),
                **linked_classification,
                **linked_source,
                "status_code": linked_response.status_code,
                "content_type": linked_response.headers.get("content-type", ""),
                "etag": linked_response.headers.get("etag"),
                "last_modified": linked_response.headers.get("last-modified"),
                **linked_retrieval_meta,
            }
            if linked_response.status_code >= 400:
                linked_metadata.update({"status": "RETRIEVAL_FAILED", "changed": False})
                results.append(linked_metadata)
                continue

            linked_snapshot = build_snapshot(
                url=str(linked_response.url),
                content=linked_response.content,
                metadata=linked_metadata,
            )
            linked_change = persist_source_snapshot(
                snapshot=linked_snapshot,
                municipality=canonical_municipality,
                source_type=linked_source["source_type"],
                description=f"Explicit tax-map link from official municipal page: {linked['label']}",
                authoritative=False,
            )
            upsert_source_catalog_entry(
                municipality=canonical_municipality,
                label=linked_label,
                source_url=linked_url,
                retrieval_url=str(linked_response.url),
                classification=linked_classification,
                source=linked_source,
                retrieved_at=linked_snapshot.retrieved_at and datetime.fromisoformat(linked_snapshot.retrieved_at),
                content_hash=linked_snapshot.content_hash,
                current_status=linked_change.status,
            )
            linked_metadata.update({
                "status": "RETRIEVED",
                "change_status": linked_change.status,
                "changed": linked_change.changed,
                "retrieved_at": linked_snapshot.retrieved_at,
                "content_hash": linked_snapshot.content_hash,
                "byte_size": linked_snapshot.byte_size,
            })
            results.append(linked_metadata)
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            results.append({
                "label": linked_label,
                "url": linked_url,
                **linked_source,
                "status": "RETRIEVAL_UNAVAILABLE",
                "changed": False,
                "error_type": exc.__class__.__name__,
            })


def refresh_discovered_municipality_sources(
    municipality: str,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """Discover municipal sources, retrieve them, and persist source versions.

    Discovery identifies candidate municipal sources; retrieval/versioning does
    not assert that any source is legally controlling for a parcel or project.
    """
    discovery = discover_municipality_sources(municipality, client=client)
    if discovery.get("status") != "DCA_SOURCES_DISCOVERED":
        return {
            "status": discovery.get("status", "DISCOVERY_UNAVAILABLE"),
            "municipality": municipality,
            "canonical_name": discovery.get("canonical_name"),
            "sources": [],
        }

    close_client = False
    if client is None:
        client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/pdf,application/json,*/*;q=0.8",
            },
        )
        close_client = True

    results: list[dict[str, Any]] = []
    municipal_origins: dict[str, str] = {}
    try:
        for label, source in discovery.get("sources", {}).items():
            url = source.get("url")
            if not url:
                continue
            canonical_municipality = discovery.get("canonical_name") or municipality
            classification = classify_discovered_source(label, url, {**source, "municipality": canonical_municipality})
            catalog_url = url
            upsert_source_catalog_entry(
                municipality=canonical_municipality,
                label=label,
                source_url=catalog_url,
                classification=classification,
                source=source,
            )
            try:
                response, retrieval_meta = retrieve_source(
                    client,
                    url,
                    alternate_urls=source.get("alternate_urls"),
                )
                if response is None:
                    response, retrieval_meta = _try_legal_content_acquisition(
                        client=client,
                        source_url=url,
                        retrieval_meta=retrieval_meta,
                    )
                if response is None:
                    metadata = {
                        "label": label,
                        "url": url,
                        **classification,
                        **retrieval_meta,
                        "status": "RETRIEVAL_FAILED",
                        "changed": False,
                    }
                    results.append(metadata)
                    continue
                origin = municipal_site_root(str(response.url), canonical_municipality)
                if origin:
                    municipal_origins.setdefault(origin, str(response.url))

                metadata = {
                    "label": label,
                    "url": str(response.url),
                    **classification,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "etag": response.headers.get("etag"),
                    "last_modified": response.headers.get("last-modified"),
                    **retrieval_meta,
                }
                if response.status_code >= 400:
                    metadata.update({"status": "RETRIEVAL_FAILED", "changed": False})
                    results.append(metadata)
                    continue

                snapshot = build_snapshot(
                    url=str(response.url),
                    content=response.content,
                    metadata=metadata,
                )
                change = persist_source_snapshot(
                    snapshot=snapshot,
                    municipality=discovery.get("canonical_name") or municipality,
                    source_type=source.get("source_type"),
                    description=f"DCA-discovered source: {label}",
                    authoritative=False,
                )
                if change.status == "HISTORY_UNAVAILABLE":
                    metadata.update({"status": "HISTORY_UNAVAILABLE", "history_error": "source_history_unavailable"})
                    results.append(metadata)
                    continue

                upsert_source_catalog_entry(
                    municipality=canonical_municipality,
                    label=label,
                    source_url=catalog_url,
                    classification=classification,
                    source=source,
                    retrieved_at=snapshot.retrieved_at and datetime.fromisoformat(snapshot.retrieved_at),
                    content_hash=snapshot.content_hash,
                    current_status=change.status,
                    retrieval_url=str(response.url),
                )
                metadata.update({
                    "status": "RETRIEVED",
                    "change_status": change.status,
                    "changed": change.changed,
                    "retrieved_at": snapshot.retrieved_at,
                    "content_hash": snapshot.content_hash,
                    "byte_size": snapshot.byte_size,
                })
                results.append(metadata)

                # Follow only explicit ordinance/code links exposed by the
                # retrieved municipal page. This is one-hop discovery: no
                # crawling, guessing, or municipality-specific URL synthesis.
                if response.headers.get("content-type", "").lower().startswith("text/html"):
                    _cache_explicit_tax_map_links_from_official_page(
                        client=client,
                        canonical_municipality=canonical_municipality,
                        page_url=str(response.url),
                        page_content=response.content,
                        page_label=label,
                        results=results,
                    )
                    explicit_links = discover_ordinance_links(
                        page_url=str(response.url),
                        content=response.content,
                    )
                    discovered_documents = discover_explicit_municipal_documents(
                        page_url=str(response.url),
                        content=response.content,
                    )
                    for document_link in discovered_documents:
                        if document_link["url"] not in {item["url"] for item in explicit_links}:
                            explicit_links.append(document_link)
                    for document_link in discover_explicit_document_links(
                        page_url=str(response.url),
                        content=response.content,
                    ):
                        if document_link["url"] not in {item["url"] for item in explicit_links}:
                            explicit_links.append(document_link)
                    for linked in explicit_links:
                        linked_url = linked["url"]
                        linked_label = f"Linked ordinance source: {linked['label']}"
                        linked_source = {
                            "source_type": "linked_municipal_ordinance",
                            "discovered_from": str(response.url),
                            "discovery_label": label,
                            "municipal_official_link_verified": True,
                            "municipal_official_page_url": str(response.url),
                        }
                        linked_classification = classify_discovered_source(
                            linked_label,
                            linked_url,
                            {**linked_source, "municipality": canonical_municipality},
                        )
                        upsert_source_catalog_entry(
                            municipality=canonical_municipality,
                            label=linked_label,
                            source_url=linked_url,
                            classification=linked_classification,
                            source=linked_source,
                        )
                        try:
                            linked_response, linked_retrieval_meta = retrieve_source(
                                client,
                                linked_url,
                                referer=str(response.url),
                            )
                            if linked_response is None:
                                linked_response, linked_retrieval_meta = _try_legal_content_acquisition(
                                    client=client,
                                    source_url=linked_url,
                                    retrieval_meta=linked_retrieval_meta,
                                )
                            if linked_response is None:
                                results.append({
                                    "label": linked_label,
                                    "url": linked_url,
                                    **linked_retrieval_meta,
                                    "status": "RETRIEVAL_FAILED",
                                    "changed": False,
                                    "discovered_from": str(response.url),
                                })
                                continue
                            linked_metadata = {
                                "label": linked_label,
                                "url": str(linked_response.url),
                                **linked_classification,
                                "status_code": linked_response.status_code,
                                "content_type": linked_response.headers.get("content-type", ""),
                                "etag": linked_response.headers.get("etag"),
                                "last_modified": linked_response.headers.get("last-modified"),
                                **linked_retrieval_meta,
                                "discovered_from": str(response.url),
                                "municipal_official_link_verified": True,
                                "municipal_official_page_url": str(response.url),
                            }
                            if linked_response.status_code >= 400:
                                linked_metadata.update({"status": "RETRIEVAL_FAILED", "changed": False})
                                results.append(linked_metadata)
                                continue
                            linked_snapshot = build_snapshot(
                                url=str(linked_response.url),
                                content=linked_response.content,
                                metadata=linked_metadata,
                            )
                            linked_change = persist_source_snapshot(
                                snapshot=linked_snapshot,
                                municipality=canonical_municipality,
                                source_type=linked_source["source_type"],
                                description=f"Explicit ordinance link from municipal page: {linked['label']}",
                                authoritative=False,
                            )
                            upsert_source_catalog_entry(
                                municipality=canonical_municipality,
                                label=linked_label,
                                source_url=linked_url,
                                classification=linked_classification,
                                source=linked_source,
                                retrieved_at=linked_snapshot.retrieved_at and datetime.fromisoformat(linked_snapshot.retrieved_at),
                                content_hash=linked_snapshot.content_hash,
                                current_status=linked_change.status,
                                retrieval_url=str(linked_response.url),
                            )
                            linked_metadata.update({
                                "status": "RETRIEVED",
                                "change_status": linked_change.status,
                                "changed": linked_change.changed,
                                "retrieved_at": linked_snapshot.retrieved_at,
                                "content_hash": linked_snapshot.content_hash,
                                "byte_size": linked_snapshot.byte_size,
                            })
                            results.append(linked_metadata)
                        except httpx.HTTPError as exc:
                            results.append({
                                "label": linked_label,
                                "url": linked_url,
                                "status": "RETRIEVAL_UNAVAILABLE",
                                "changed": False,
                                "error_type": exc.__class__.__name__,
                                "discovered_from": str(response.url),
                            })
            except httpx.HTTPError as exc:
                results.append({
                    "label": label,
                    "url": url,
                    "status": "RETRIEVAL_UNAVAILABLE",
                    "changed": False,
                    "error_type": exc.__class__.__name__,
                })

        # DCA may point to a municipal department page that does not itself
        # expose the zoning-map link.  For each already-verified municipal host,
        # inspect only the site's root page and then retrieve explicit same-host
        # zoning-page links found there.  This is a bounded two-step expansion,
        # not a crawl and not URL synthesis.
        canonical_municipality = discovery.get("canonical_name") or municipality
        for origin, seed_url in municipal_origins.items():
            try:
                root_response, root_retrieval_meta = retrieve_source(client, origin, referer=seed_url)
            except (httpx.HTTPError, TypeError):
                root_response = None
                root_retrieval_meta = {"retrieval_mode": "retrieval_unavailable"}
            if root_response is None:
                results.append({
                    "label": "Municipal website root",
                    "url": origin,
                    **root_retrieval_meta,
                    "status": "RETRIEVAL_FAILED",
                    "changed": False,
                    "discovered_from": seed_url,
                })
                continue

            root_source = {
                "source_type": "municipal_official_site_root",
                "discovered_from": seed_url,
                "municipal_official_link_verified": True,
                "municipal_official_page_url": seed_url,
            }
            root_classification = classify_discovered_source(
                "Municipal website root", origin, {**root_source, "municipality": canonical_municipality}
            )
            root_metadata = {
                "label": "Municipal website root",
                "url": str(root_response.url),
                **root_classification,
                "status_code": root_response.status_code,
                "content_type": root_response.headers.get("content-type", ""),
                **root_retrieval_meta,
                "discovered_from": seed_url,
            }
            if root_response.status_code >= 400:
                root_metadata.update({"status": "RETRIEVAL_FAILED", "changed": False})
                results.append(root_metadata)
                continue

            root_snapshot = build_snapshot(
                url=str(root_response.url), content=root_response.content, metadata=root_metadata
            )
            root_change = persist_source_snapshot(
                snapshot=root_snapshot,
                municipality=canonical_municipality,
                source_type=root_source["source_type"],
                description="Official municipal website root used for bounded zoning-page discovery",
                authoritative=False,
            )
            upsert_source_catalog_entry(
                municipality=canonical_municipality,
                label="Municipal website root",
                source_url=origin,
                retrieval_url=str(root_response.url),
                classification=root_classification,
                source=root_source,
                retrieved_at=root_snapshot.retrieved_at and datetime.fromisoformat(root_snapshot.retrieved_at),
                content_hash=root_snapshot.content_hash,
                current_status=root_change.status,
            )
            root_metadata.update({
                "status": "RETRIEVED",
                "change_status": root_change.status,
                "changed": root_change.changed,
                "retrieved_at": root_snapshot.retrieved_at,
                "content_hash": root_snapshot.content_hash,
                "byte_size": root_snapshot.byte_size,
            })
            results.append(root_metadata)

            _cache_explicit_legal_links_from_official_page(
                client=client,
                canonical_municipality=canonical_municipality,
                page_url=str(root_response.url),
                page_content=root_response.content,
                page_label="Municipal website root",
                results=results,
            )

            _cache_explicit_tax_map_links_from_official_page(
                client=client,
                canonical_municipality=canonical_municipality,
                page_url=str(root_response.url),
                page_content=root_response.content,
                page_label="Municipal website root",
                results=results,
            )

            zoning_pages = discover_zoning_page_links(
                page_url=str(root_response.url), content=root_response.content
            )
            for zoning_page in zoning_pages:
                page_url = zoning_page["url"]
                page_label = f"Official municipal zoning page: {zoning_page['label']}"
                page_source = {
                    "source_type": "municipal_official_zoning_page",
                    "discovered_from": str(root_response.url),
                    "municipal_official_link_verified": True,
                    "municipal_official_page_url": str(root_response.url),
                }
                page_classification = classify_discovered_source(
                    page_label, page_url, {**page_source, "municipality": canonical_municipality}
                )
                upsert_source_catalog_entry(
                    municipality=canonical_municipality,
                    label=page_label,
                    source_url=page_url,
                    classification=page_classification,
                    source=page_source,
                )
                try:
                    page_response, page_retrieval_meta = retrieve_source(
                        client, page_url, referer=str(root_response.url)
                    )
                except (httpx.HTTPError, TypeError) as exc:
                    results.append({
                        "label": page_label,
                        "url": page_url,
                        "status": "RETRIEVAL_UNAVAILABLE",
                        "changed": False,
                        "error_type": exc.__class__.__name__,
                        "discovered_from": str(root_response.url),
                    })
                    continue
                if page_response is None:
                    results.append({
                        "label": page_label,
                        "url": page_url,
                        **page_retrieval_meta,
                        "status": "RETRIEVAL_FAILED",
                        "changed": False,
                        "discovered_from": str(root_response.url),
                    })
                    continue

                page_metadata = {
                    "label": page_label,
                    "url": str(page_response.url),
                    **page_classification,
                    "status_code": page_response.status_code,
                    "content_type": page_response.headers.get("content-type", ""),
                    **page_retrieval_meta,
                    "discovered_from": str(root_response.url),
                    "municipal_official_link_verified": True,
                    "municipal_official_page_url": str(root_response.url),
                }
                page_snapshot = build_snapshot(
                    url=str(page_response.url), content=page_response.content, metadata=page_metadata
                )
                page_change = persist_source_snapshot(
                    snapshot=page_snapshot,
                    municipality=canonical_municipality,
                    source_type=page_source["source_type"],
                    description=f"Explicit zoning page linked from official municipal website: {zoning_page['label']}",
                    authoritative=False,
                )
                upsert_source_catalog_entry(
                    municipality=canonical_municipality,
                    label=page_label,
                    source_url=page_url,
                    retrieval_url=str(page_response.url),
                    classification=page_classification,
                    source=page_source,
                    retrieved_at=page_snapshot.retrieved_at and datetime.fromisoformat(page_snapshot.retrieved_at),
                    content_hash=page_snapshot.content_hash,
                    current_status=page_change.status,
                )
                page_metadata.update({
                    "status": "RETRIEVED",
                    "change_status": page_change.status,
                    "changed": page_change.changed,
                    "retrieved_at": page_snapshot.retrieved_at,
                    "content_hash": page_snapshot.content_hash,
                    "byte_size": page_snapshot.byte_size,
                })
                results.append(page_metadata)

                _cache_explicit_legal_links_from_official_page(
                    client=client,
                    canonical_municipality=canonical_municipality,
                    page_url=str(page_response.url),
                    page_content=page_response.content,
                    page_label=page_label,
                    results=results,
                )

                _cache_explicit_tax_map_links_from_official_page(
                    client=client,
                    canonical_municipality=canonical_municipality,
                    page_url=str(page_response.url),
                    page_content=page_response.content,
                    page_label=page_label,
                    results=results,
                )

        return {
            "status": "SOURCES_REFRESHED",
            "municipality": municipality,
            "canonical_name": discovery.get("canonical_name"),
            "sources": results,
        }
    finally:
        if close_client:
            client.close()
