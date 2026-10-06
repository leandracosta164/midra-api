from app.services.source_versioning import (
    SourceSnapshot,
    build_snapshot,
    compare_snapshots,
    content_hash,
)


def test_content_hash_is_stable():
    assert content_hash(b"MIDRA") == content_hash(b"MIDRA")
    assert content_hash(b"MIDRA") != content_hash(b"MIDRA changed")


def test_initial_snapshot_is_not_marked_changed():
    current = build_snapshot(url="https://example.test", content=b"abc")
    result = compare_snapshots(None, current)
    assert result.status == "INITIAL"
    assert result.changed is False


def test_identical_snapshots_are_unchanged():
    previous = build_snapshot(url="https://example.test", content=b"abc")
    current = SourceSnapshot(
        url=previous.url,
        retrieved_at="2026-09-11T00:00:00+00:00",
        content_hash=previous.content_hash,
        byte_size=previous.byte_size,
    )
    result = compare_snapshots(previous, current)
    assert result.status == "UNCHANGED"
    assert result.changed is False


def test_content_change_is_detected():
    previous = build_snapshot(url="https://example.test", content=b"abc")
    current = build_snapshot(url="https://example.test", content=b"abcd")
    result = compare_snapshots(previous, current)
    assert result.status == "CHANGED"
    assert result.changed is True


def test_snapshot_captures_http_metadata():
    snapshot = build_snapshot(
        url="https://example.test/final",
        content=b"abc",
        metadata={
            "status_code": 200,
            "content_type": "text/html",
            "etag": '"v1"',
            "last_modified": "Thu, 11 Sep 2026 00:00:00 GMT",
        },
    )
    assert snapshot.status_code == 200
    assert snapshot.content_type == "text/html"
    assert snapshot.etag == '"v1"'
    assert snapshot.last_modified == "Thu, 11 Sep 2026 00:00:00 GMT"
    assert snapshot.byte_size == 3
    assert snapshot.retrieved_at.endswith("+00:00")
