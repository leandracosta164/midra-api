from types import SimpleNamespace

from app.services.municipal_source_retrieval import retrieve_source


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None):
        self.calls.append((url, headers or {}))
        return self.responses.pop(0)


def response(status, url="https://example.com/source"):
    return SimpleNamespace(status_code=status, url=url)


def test_403_gets_one_browser_retry():
    client = FakeClient([response(403), response(200)])
    result, meta = retrieve_source(client, "https://example.com/source")
    assert result.status_code == 200
    assert meta["retrieval_mode"] == "primary_or_browser_retry"
    assert len(client.calls) == 2
    assert "User-Agent" in client.calls[1][1]


def test_explicit_alternate_is_used_after_403():
    client = FakeClient([response(403), response(403), response(200, "https://example.gov/code.pdf")])
    result, meta = retrieve_source(
        client,
        "https://example.com/source",
        alternate_urls=["https://example.gov/code.pdf"],
        referer="https://example.gov/zoning",
    )
    assert result.status_code == 200
    assert meta["retrieval_mode"] == "explicit_alternate"
    assert client.calls[-1][0] == "https://example.gov/code.pdf"
    assert client.calls[1][1]["Referer"] == "https://example.gov/zoning"


def test_no_url_guessing_when_all_attempts_fail():
    client = FakeClient([response(403), response(403)])
    result, meta = retrieve_source(client, "https://ecode360.com/35019251")
    assert result is None
    assert meta["retrieval_mode"] == "retrieval_failed"
    assert len(client.calls) == 2
