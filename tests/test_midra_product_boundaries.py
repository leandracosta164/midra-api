from app.services.midra_product_boundaries import (
    build_product_boundary_manifest,
    build_role_access_manifest,
)


def test_intelligence_and_engineering_are_explicitly_separate_products():
    manifest = build_product_boundary_manifest()
    assert manifest["architecture_status"] == "SEPARATE_PRODUCTS_SHARED_INFRASTRUCTURE"
    assert manifest["products"]["MIDRA_INTELLIGENCE"]["deployment_identity"] == "INDEPENDENT_APP_OR_WEBSITE"
    assert manifest["products"]["MIDRA_ENGINEERING"]["deployment_identity"] == "SEPARATE_ENGINEERING_FIRM_APP_OR_WEBSITE"


def test_private_engineering_pricing_and_proposals_do_not_belong_to_intelligence():
    manifest = build_product_boundary_manifest()
    intelligence = manifest["products"]["MIDRA_INTELLIGENCE"]
    engineering = manifest["products"]["MIDRA_ENGINEERING"]
    assert "engineering_private_pricing" in intelligence["must_not_own"]
    assert "engineering_proposal_draft" in intelligence["must_not_own"]
    assert "private_pricing_library" in engineering["owns"]
    assert "engineering_proposal_draft" in engineering["owns"]


def test_shared_platform_prevents_duplicate_property_research():
    manifest = build_product_boundary_manifest()
    assert manifest["shared_platform"]["handoff_by_reference"] is True
    assert manifest["shared_platform"]["duplicate_research_required"] is False
    assert manifest["products"]["MIDRA_ENGINEERING"]["must_not_require_duplicate_property_research"] is True


def test_request_proposal_handoff_has_agreed_copy_and_no_extra_permission_step():
    handoff = build_product_boundary_manifest()["proposal_handoff"]
    assert handoff["source_product"] == "MIDRA_INTELLIGENCE"
    assert handoff["destination_product"] == "MIDRA_ENGINEERING"
    assert handoff["cta_headline"] == "Ready to move forward with your project?"
    assert handoff["cta_body"] == "Engineering design services are available through MIDRA Engineering."
    assert handoff["cta_action"] == "REQUEST AN ENGINEERING PROPOSAL"
    assert handoff["separate_share_permission_step"] is False


def test_owner_admin_and_engineering_roles_remain_conceptually_distinct():
    roles = build_role_access_manifest()
    assert "proposal_workspace" in roles["MIDRA_ENGINEERING"]
    assert "system_diagnostics" in roles["MIDRA_ADMIN"]
    assert roles["MIDRA_ENGINEERING"] != roles["MIDRA_ADMIN"]
