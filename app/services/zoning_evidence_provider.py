"""Provider contract for dynamic parcel-specific zoning evidence.

Providers translate a concrete public source representation into the small,
validated evidence contract consumed by the generic zoning evidence adapter.
This module defines the contract only; it does not infer zoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ZoningEvidenceRecord:
    municipality: str
    block: str
    lot: str
    zoning_district: str
    source: dict[str, Any]
    evidence_type: str = "PARCEL_SPECIFIC_SOURCE"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_adapter_input(self) -> dict[str, Any]:
        return {
            "municipality": self.municipality,
            "block": self.block,
            "lot": self.lot,
            "zoning_district": self.zoning_district,
            "evidence_type": self.evidence_type,
            "source": self.source,
        }


class ZoningEvidenceProvider(Protocol):
    """Minimal interface implemented by future source-specific providers."""

    def supports(self, source: dict[str, Any]) -> bool:
        """Return True only when this provider understands the source format."""
        ...

    def extract(
        self,
        *,
        municipality: str,
        block: str,
        lot: str,
        source: dict[str, Any],
        content: bytes,
    ) -> ZoningEvidenceRecord | None:
        """Extract parcel-specific evidence, or None when evidence is insufficient."""
        ...
