from types import SimpleNamespace

from app.services.legal_content_provider import (
    ECode360Provider,
    LegalContentRequest,
    acquire_legal_content,
)


def test_ecode_provider_matches_explicit_source_or_observed_redirect_only():
    provider = ECode360Provider(retriever=lambda *a, **k: (None, {}))

    direct = LegalContentRequest("https://ecode360.com/AB1234", {})
    redirected = LegalContentRequest(
        "https://example.gov/municipal-code",
        {"final_url": "https://www.ecode360.com/AB1234"},
    )
    unrelated = LegalContentRequest(
        "https://example.gov/municipal-code",
        {"final_url": "https://codes.example.net/AB1234"},
    )

    assert provider.match(direct) == "https://ecode360.com/AB1234"
    assert provider.match(redirected) == "https://www.ecode360.com/AB1234"
    assert provider.match(unrelated) is None


def test_provider_registry_preserves_no_match_metadata():
    original = {"retrieval_mode": "retrieval_failed", "final_url": "https://example.gov/code"}
    response, meta = acquire_legal_content(
        object(),
        source_url="https://example.gov/code",
        retrieval_meta=original,
        providers=(ECode360Provider(retriever=lambda *a, **k: (_ for _ in ()).throw(AssertionError())),),
    )
    assert response is None
    assert meta == original


def test_ecode_provider_returns_provider_neutral_metadata(monkeypatch):
    def fake_retriever(client, *, source_url, api_key, api_secret):
        return SimpleNamespace(status_code=200, url=source_url, content=b"law", headers={}), {
            "retrieval_mode": "ecode_api",
            "customer": "AB1234",
        }

    provider = ECode360Provider(retriever=fake_retriever)
    response, meta = acquire_legal_content(
        object(),
        source_url="https://example.gov/municipal-code",
        retrieval_meta={"final_url": "https://ecode360.com/AB1234"},
        providers=(provider,),
    )

    assert response is not None
    assert meta["legal_content_provider"] == "ecode360"
    assert meta["provider"] == "ecode360"
    assert meta["provider_representation_url"] == "https://ecode360.com/AB1234"
    assert meta["provider_result"]["customer"] == "AB1234"
    assert meta["retrieval_mode"] == "ecode_api"
