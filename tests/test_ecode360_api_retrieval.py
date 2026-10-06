from types import SimpleNamespace

from app.services.ecode360_api_retrieval import (
    extract_ecode_customer_id,
    retrieve_ecode_zoning_content,
)


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None):
        self.calls.append((url, headers or {}))
        return self.responses.pop(0)


def test_extracts_only_explicit_ecode_customer_id():
    assert extract_ecode_customer_id("https://www.ecode360.com/PE0514") == "PE0514"
    assert extract_ecode_customer_id("https://ecode360.com/PE0514/laws") == "PE0514"
    assert extract_ecode_customer_id("https://ecode360.com/35019251") == "35019251"
    assert extract_ecode_customer_id("https://example.com/PE0514") is None


def test_requires_credentials():
    client = FakeClient([])
    result, meta = retrieve_ecode_zoning_content(
        client,
        source_url="https://www.ecode360.com/PE0514",
        api_key=None,
        api_secret=None,
    )
    assert result is None
    assert meta["reason"] == "API_CREDENTIALS_NOT_CONFIGURED"
    assert client.calls == []


def test_retrieves_explicit_zoning_chapter_content():
    toc = {
        "children": [
            {"type": "chapter", "guid": "430", "number": "430", "title": "Zoning", "children": []},
            {"type": "chapter", "guid": "500", "number": "500", "title": "Fees", "children": []},
        ]
    }
    content = {
        "number": "Chapter 430",
        "title": "Zoning",
        "content": "§ 430-16. R-M(M) Mid-Rise Residential.",
        "children": [
            {
                "number": "B(1)",
                "title": "Accessory uses",
                "content": "All accessory uses as permitted in the R-60 Zone.",
                "children": [],
            },
            {
                "number": "§ 430-13",
                "title": "R-60",
                "content": "Private recreational facilities, such as swimming pools, are permitted accessory uses.",
                "children": [],
            },
        ],
    }
    client = FakeClient([FakeResponse(200, toc), FakeResponse(200, content)])
    result, meta = retrieve_ecode_zoning_content(
        client,
        source_url="https://www.ecode360.com/PE0514",
        api_key="key",
        api_secret="secret",
    )
    assert result.status_code == 200
    text = result.content.decode("utf-8")
    assert "R-M(M)" in text
    assert "swimming pools" in text
    assert meta["retrieval_mode"] == "ecode_api"
    assert meta["retrieved_chapters"][0]["guid"] == "430"
    assert client.calls[0][1]["api-key"] == "key"
    assert client.calls[0][1]["api-secret"] == "secret"
