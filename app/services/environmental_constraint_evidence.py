"""Environmental-constraint evidence contract for MIDRA Property.

Phase 1.25 deliberately does not infer parcel-specific flood or wetland conditions.
Until an authoritative spatial provider has actually evaluated the resolved parcel,
the only defensible status is NOT_EVALUATED.
"""
from __future__ import annotations
from typing import Any

NOT_EVALUATED = "NOT_EVALUATED"

def build_environmental_constraint_evidence(*, property_resolution: dict[str, Any] | None) -> dict[str, Any]:
    resolved = bool((property_resolution or {}).get("status") == "PROPERTY_RESOLVED")
    reason = (
        "The property is resolved, but no authoritative parcel-specific environmental spatial evaluation has been performed."
        if resolved else
        "The property is not resolved to a verified parcel, so parcel-specific environmental spatial evaluation cannot be performed."
    )
    def item(kind: str, label: str) -> dict[str, Any]:
        return {
            "constraint": kind,
            "label": label,
            "status": NOT_EVALUATED,
            "evidence_available": False,
            "source": None,
            "meaning": reason,
            "verification_required": True,
        }
    return {
        "status": NOT_EVALUATED,
        "parcel_resolved": resolved,
        "flood": item("flood", "Flood hazard"),
        "wetlands": item("wetlands", "Wetlands"),
        "limitations": [
            "NOT_EVALUATED is not a finding that a constraint is present or absent.",
            "Flood and wetlands must not be promoted until supported by authoritative property-specific evidence.",
        ],
    }
