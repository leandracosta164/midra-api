"""Source fingerprinting and change classification for MIDRA evidence.

This module is deliberately storage-agnostic.  It provides the stable
metadata contract needed before persistent source history is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Mapping


@dataclass(frozen=True)
class SourceSnapshot:
    """A single retrieved public source representation."""

    url: str
    retrieved_at: str
    content_hash: str
    byte_size: int
    status_code: int | None = None
    content_type: str = ""
    etag: str | None = None
    last_modified: str | None = None
    content: bytes | None = None


@dataclass(frozen=True)
class SourceChange:
    """Comparison between a previous and current source snapshot."""

    status: str
    changed: bool


def utc_timestamp() -> str:
    """Return an explicit UTC timestamp for evidence metadata."""
    return datetime.now(timezone.utc).isoformat()


def content_hash(content: bytes) -> str:
    """Return a stable SHA-256 fingerprint for retrieved content."""
    return hashlib.sha256(content).hexdigest()


def build_snapshot(
    *,
    url: str,
    content: bytes,
    metadata: Mapping[str, object] | None = None,
) -> SourceSnapshot:
    """Build a normalized source snapshot from response content/metadata."""
    metadata = metadata or {}
    status_code = metadata.get("status_code")
    return SourceSnapshot(
        url=url,
        retrieved_at=utc_timestamp(),
        content_hash=content_hash(content),
        byte_size=len(content),
        status_code=int(status_code) if status_code is not None else None,
        content_type=str(metadata.get("content_type") or ""),
        etag=str(metadata.get("etag")) if metadata.get("etag") else None,
        last_modified=(
            str(metadata.get("last_modified"))
            if metadata.get("last_modified")
            else None
        ),
        content=content,
    )


def compare_snapshots(
    previous: SourceSnapshot | None,
    current: SourceSnapshot,
) -> SourceChange:
    """Classify a current retrieval without treating first retrieval as a change."""
    if previous is None:
        return SourceChange(status="INITIAL", changed=False)
    if previous.content_hash != current.content_hash:
        return SourceChange(status="CHANGED", changed=True)
    return SourceChange(status="UNCHANGED", changed=False)
