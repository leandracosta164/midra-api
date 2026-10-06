from app.services import municipality_source_refresh as refresh


class FakeResponse:
    def __init__(self, url, content=b"municipal-source"):
        self.url = url
        self.content = content
        self.status_code = 200
        self.headers = {"content-type": "text/html"}


class FakeClient:
    def get(self, url, params=None):
        return FakeResponse(url)


def test_refresh_retrieves_discovered_sources_and_versions(monkeypatch):
    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Test Township",
            "sources": {
                "Zoning Map": {
                    "url": "https://example.test/map.pdf",
                    "source_type": "dca_zoning_information_directory_link",
                }
            },
        },
    )

    recorded = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )

    result = refresh.refresh_discovered_municipality_sources("Test Township", client=FakeClient())
    assert result["status"] == "SOURCES_REFRESHED"
    assert result["sources"][0]["status"] == "RETRIEVED"
    assert result["sources"][0]["change_status"] == "INITIAL"


def test_refresh_preserves_discovery_failure(monkeypatch):
    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {"status": "DCA_SOURCE_INDEX_NOT_FOUND"},
    )
    result = refresh.refresh_discovered_municipality_sources("Unknown Township", client=FakeClient())
    assert result["status"] == "DCA_SOURCE_INDEX_NOT_FOUND"
    assert result["sources"] == []


def test_refresh_updates_source_catalog(monkeypatch):
    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Test Township",
            "sources": {"Zoning Map": {"url": "https://example.test/map.pdf", "source_type": "dca_zoning_information_directory_link"}},
        },
    )
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: True)
    monkeypatch.setattr(refresh, "persist_source_snapshot", lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False))
    result = refresh.refresh_discovered_municipality_sources("Test Township", client=FakeClient())
    assert result["status"] == "SOURCES_REFRESHED"


def test_refresh_discovers_and_caches_zoning_page_from_official_site_root(monkeypatch):
    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.perthamboynj.org/":
                return FakeResponse(
                    url,
                    b'<a href="/cms/One.aspx?pageId=20618142&amp;portalId=11205008">Perth Amboy Zoning Map</a>',
                )
            if "pageId=20618142" in url:
                return FakeResponse(
                    url,
                    b'<h1>Perth Amboy Interactive Zoning Viewer</h1><a href="https://x.example/?appid=09bd902a48ef45348d2d59283c89673c">Explore the Map</a>',
                )
            return FakeResponse(url, b"<h1>Code Enforcement</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Perth Amboy City",
            "sources": {
                "Code Enforcement": {
                    "url": "https://www.perthamboynj.org/government/departments/code_enforcement",
                    "source_type": "dca_zoning_information_directory_link",
                }
            },
        },
    )
    catalog_calls = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: catalog_calls.append(kwargs) or True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )

    result = refresh.refresh_discovered_municipality_sources("Perth Amboy City", client=RoutedClient())

    zoning_pages = [
        call for call in catalog_calls
        if (call.get("source") or {}).get("source_type") == "municipal_official_zoning_page"
    ]
    assert len(zoning_pages) == 2  # pre-retrieval catalog upsert + versioned-content upsert
    assert zoning_pages[-1]["source_url"] == "https://www.perthamboynj.org/cms/One.aspx?pageId=20618142&portalId=11205008"
    assert any(item.get("label", "").startswith("Official municipal zoning page:") and item.get("status") == "RETRIEVED" for item in result["sources"])


def test_refresh_discovers_explicit_legal_source_from_official_root(monkeypatch):
    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.perthamboynj.org/":
                return FakeResponse(
                    url,
                    b'<a href="http://www.ecode360.com/PE0514">i Local Laws &amp; Ordinances</a>',
                )
            if "ecode360.com/PE0514" in url:
                return FakeResponse(url, b"Official zoning code content")
            return FakeResponse(url, b"<h1>Code Enforcement</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Perth Amboy City",
            "sources": {
                "Code Enforcement": {
                    "url": "https://www.perthamboynj.org/government/departments/code_enforcement",
                    "source_type": "dca_zoning_information_directory_link",
                }
            },
        },
    )
    catalog_calls = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: catalog_calls.append(kwargs) or True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )

    result = refresh.refresh_discovered_municipality_sources("Perth Amboy City", client=RoutedClient())

    legal = [call for call in catalog_calls if call.get("source_url") == "http://www.ecode360.com/PE0514"]
    assert legal
    assert legal[-1]["classification"]["source_role"] == "zoning_ordinance"
    assert legal[-1]["source"]["municipal_official_link_verified"] is True
    assert any(item.get("url") == "http://www.ecode360.com/PE0514" and item.get("status") == "RETRIEVED" for item in result["sources"])


def test_refresh_discovers_explicit_legal_source_from_zoning_page(monkeypatch):
    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.exampletownnj.org/":
                return FakeResponse(url, b'<a href="/zoning">Zoning Map</a>')
            if url == "https://www.exampletownnj.org/zoning":
                return FakeResponse(url, b'<a href="https://ecode360.com/EX1234">City Code</a>')
            if url == "https://ecode360.com/EX1234":
                return FakeResponse(url, b"Official zoning code content")
            return FakeResponse(url, b"<h1>Planning</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Example Town",
            "sources": {
                "Planning": {
                    "url": "https://www.exampletownnj.org/planning",
                    "source_type": "dca_zoning_information_directory_link",
                }
            },
        },
    )
    catalog_calls = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: catalog_calls.append(kwargs) or True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )

    refresh.refresh_discovered_municipality_sources("Example Town", client=RoutedClient())
    legal = [call for call in catalog_calls if call.get("source_url") == "https://ecode360.com/EX1234"]
    assert legal
    assert legal[-1]["source"]["discovered_from"] == "https://www.exampletownnj.org/zoning"


def test_ecode_failure_reports_api_dependency_without_promoting(monkeypatch):
    class Response:
        def __init__(self, url, status=200, content=b"page"):
            self.url = url
            self.status_code = status
            self.content = content
            self.headers = {"content-type": "text/html"}

    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.exampletownnj.org/":
                return Response(url, content=b'<a href="https://ecode360.com/EX1234">Municipal Code</a>')
            if "ecode360.com" in url:
                return Response(url, status=403, content=b"")
            return Response(url, content=b"<h1>Planning</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Example Town",
            "sources": {"Planning": {"url": "https://www.exampletownnj.org/planning", "source_type": "dca_zoning_information_directory_link"}},
        },
    )
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )
    monkeypatch.setattr(refresh.settings, "ECODE360_API_KEY", None)
    monkeypatch.setattr(refresh.settings, "ECODE360_API_SECRET", None)

    result = refresh.refresh_discovered_municipality_sources("Example Town", client=RoutedClient())
    failed = [item for item in result["sources"] if item.get("url") == "https://ecode360.com/EX1234" and item.get("status") == "RETRIEVAL_FAILED"]
    assert failed
    assert failed[-1]["ecode_api"]["reason"] == "API_CREDENTIALS_NOT_CONFIGURED"


def test_refresh_caches_explicit_legal_document_from_official_root_when_codifier_fails(monkeypatch):
    class Response:
        def __init__(self, url, status=200, content=b"page", content_type="text/html"):
            self.url = url
            self.status_code = status
            self.content = content
            self.headers = {"content-type": content_type}

    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.exampletownnj.org/":
                return Response(
                    url,
                    content=(
                        b'<a href="https://ecode360.com/EX1234">Municipal Code</a>'
                        b'<a href="/documents/zoning-ordinance.pdf">Zoning Ordinance</a>'
                    ),
                )
            if "ecode360.com" in url:
                return Response(url, status=403, content=b"")
            if url == "https://www.exampletownnj.org/documents/zoning-ordinance.pdf":
                return Response(url, content=b"official ordinance pdf", content_type="application/pdf")
            return Response(url, content=b"<h1>Planning</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Example Town",
            "sources": {"Planning": {"url": "https://www.exampletownnj.org/planning", "source_type": "dca_zoning_information_directory_link"}},
        },
    )
    catalog_calls = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: catalog_calls.append(kwargs) or True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )
    monkeypatch.setattr(refresh.settings, "ECODE360_API_KEY", None)
    monkeypatch.setattr(refresh.settings, "ECODE360_API_SECRET", None)

    result = refresh.refresh_discovered_municipality_sources("Example Town", client=RoutedClient())

    assert any(
        item.get("url") == "https://www.exampletownnj.org/documents/zoning-ordinance.pdf"
        and item.get("status") == "RETRIEVED"
        for item in result["sources"]
    )
    document_calls = [
        call for call in catalog_calls
        if call.get("source_url") == "https://www.exampletownnj.org/documents/zoning-ordinance.pdf"
    ]
    assert document_calls
    assert document_calls[-1]["source"]["municipal_official_link_verified"] is True
    assert document_calls[-1]["source"]["discovered_from"] == "https://www.exampletownnj.org/"


def test_refresh_caches_explicit_legal_document_from_official_zoning_page(monkeypatch):
    class Response:
        def __init__(self, url, content=b"page", content_type="text/html"):
            self.url = url
            self.status_code = 200
            self.content = content
            self.headers = {"content-type": content_type}

    class RoutedClient:
        def get(self, url, params=None, headers=None):
            if url == "https://www.exampletownnj.org/":
                return Response(url, b'<a href="/zoning">Zoning Map</a>')
            if url == "https://www.exampletownnj.org/zoning":
                return Response(url, b'<a href="/files/land-use-code.pdf">Zoning Code</a>')
            if url == "https://www.exampletownnj.org/files/land-use-code.pdf":
                return Response(url, b"official zoning code pdf", "application/pdf")
            return Response(url, b"<h1>Planning</h1>")

    monkeypatch.setattr(
        refresh,
        "discover_municipality_sources",
        lambda municipality, client=None: {
            "status": "DCA_SOURCES_DISCOVERED",
            "canonical_name": "Example Town",
            "sources": {"Planning": {"url": "https://www.exampletownnj.org/planning", "source_type": "dca_zoning_information_directory_link"}},
        },
    )
    catalog_calls = []
    monkeypatch.setattr(refresh, "upsert_source_catalog_entry", lambda **kwargs: catalog_calls.append(kwargs) or True)
    monkeypatch.setattr(
        refresh,
        "persist_source_snapshot",
        lambda **kwargs: __import__("app.services.source_versioning", fromlist=["SourceChange"]).SourceChange("INITIAL", False),
    )

    result = refresh.refresh_discovered_municipality_sources("Example Town", client=RoutedClient())

    assert any(
        item.get("url") == "https://www.exampletownnj.org/files/land-use-code.pdf"
        and item.get("status") == "RETRIEVED"
        for item in result["sources"]
    )
    document_calls = [
        call for call in catalog_calls
        if call.get("source_url") == "https://www.exampletownnj.org/files/land-use-code.pdf"
    ]
    assert document_calls
    assert document_calls[-1]["source"]["discovered_from"] == "https://www.exampletownnj.org/zoning"


def test_legal_content_acquisition_preserves_ecode_compatibility_diagnostic(monkeypatch):
    def fake_acquire(client, *, source_url, retrieval_meta):
        return None, {
            **retrieval_meta,
            "legal_content_provider": "ecode360",
            "provider_result": {
                "retrieval_mode": "ecode_api_unavailable",
                "reason": "API_CREDENTIALS_NOT_CONFIGURED",
                "customer": "EX1234",
            },
        }

    monkeypatch.setattr(refresh, "acquire_legal_content", fake_acquire)

    response, meta = refresh._try_legal_content_acquisition(
        client=object(),
        source_url="https://www.exampletownnj.org/government/municipal_code",
        retrieval_meta={"final_url": "https://ecode360.com/EX1234"},
    )

    assert response is None
    assert meta["legal_content_provider"] == "ecode360"
    assert meta["ecode_api"]["reason"] == "API_CREDENTIALS_NOT_CONFIGURED"


def test_legal_content_acquisition_passes_original_identity_and_observed_metadata(monkeypatch):
    captured = {}

    def fake_acquire(client, *, source_url, retrieval_meta):
        captured["source_url"] = source_url
        captured["retrieval_meta"] = retrieval_meta
        return None, retrieval_meta

    monkeypatch.setattr(refresh, "acquire_legal_content", fake_acquire)
    source = "https://www.exampletownnj.org/government/municipal_code"
    observed = {"final_url": "https://ecode360.com/EX1234", "retrieval_mode": "retrieval_failed"}

    refresh._try_legal_content_acquisition(
        client=object(),
        source_url=source,
        retrieval_meta=observed,
    )

    assert captured["source_url"] == source
    assert captured["retrieval_meta"] == observed
