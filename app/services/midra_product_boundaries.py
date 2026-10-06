"""Phase 5.26 product-boundary contract for the MIDRA platform.

MIDRA Intelligence and MIDRA Engineering are separate products/app surfaces.
They may use shared platform infrastructure and immutable analysis/evidence IDs,
but public Intelligence concerns must not be coupled to Engineering's private
proposal/pricing/project concerns.
"""
from __future__ import annotations

from typing import Any


MIDRA_INTELLIGENCE = "MIDRA_INTELLIGENCE"
MIDRA_ENGINEERING = "MIDRA_ENGINEERING"
SHARED_PLATFORM = "MIDRA_SHARED_PLATFORM"


def build_product_boundary_manifest() -> dict[str, Any]:
    return {
        "architecture_status": "SEPARATE_PRODUCTS_SHARED_INFRASTRUCTURE",
        "products": {
            MIDRA_INTELLIGENCE: {
                "deployment_identity": "INDEPENDENT_APP_OR_WEBSITE",
                "public_product": True,
                "owns": [
                    "property_search",
                    "property_intelligence",
                    "zoning_intelligence",
                    "project_feasibility",
                    "property_workspace",
                    "midra_integrated_map",
                    "map_and_document_access",
                    "preliminary_report",
                    "complete_report",
                    "engineering_proposal_request_entrypoint",
                ],
                "must_not_own": [
                    "engineering_private_pricing",
                    "engineering_proposal_draft",
                    "engineering_contracts",
                    "engineering_work_product",
                    "engineering_billing",
                ],
            },
            MIDRA_ENGINEERING: {
                "deployment_identity": "SEPARATE_ENGINEERING_FIRM_APP_OR_WEBSITE",
                "public_product": False,
                "owns": [
                    "engineering_intake",
                    "engineering_workspace",
                    "private_scope_library",
                    "private_pricing_library",
                    "engineering_proposal_draft",
                    "engineer_review_and_approval",
                    "client_project_files",
                    "engineering_work_product",
                ],
                "must_not_require_duplicate_property_research": True,
            },
        },
        "shared_platform": {
            "identity": SHARED_PLATFORM,
            "owns": [
                "property_record",
                "analysis_snapshot",
                "evidence_artifacts",
                "source_provenance",
                "retrieval_metadata",
                "map_artifacts",
            ],
            "handoff_by_reference": True,
            "duplicate_research_required": False,
        },
        "proposal_handoff": {
            "source_product": MIDRA_INTELLIGENCE,
            "destination_product": MIDRA_ENGINEERING,
            "cta_headline": "Ready to move forward with your project?",
            "cta_body": "Engineering design services are available through MIDRA Engineering.",
            "cta_action": "REQUEST AN ENGINEERING PROPOSAL",
            "separate_share_permission_step": False,
        },
    }


def build_role_access_manifest() -> dict[str, Any]:
    """Keep customer/professional/engineering/admin responsibilities distinct."""
    return {
        "CUSTOMER": ["property_search", "entitled_reports", "property_workspace"],
        "PROFESSIONAL_USER": ["property_search", "complete_report", "professional_workspace", "source_documents"],
        "MIDRA_ENGINEERING": ["shared_complete_property_record", "all_shared_evidence", "proposal_workspace", "client_project_files"],
        "MIDRA_ADMIN": ["source_health", "municipality_coverage", "retrieval_failures", "data_quality", "verification_queues", "system_diagnostics", "product_administration"],
    }
