from app.services.product_boundary_integration import *

def export():
    return create_property_export(
        analysis_id="PA-77",property_address="150 Bayside Drive",
        requested_work="Retaining walls",
        analysis_fields={"municipality":"Atlantic Highlands","block":"39.05","lot":"12"})

def test_property_export_is_standalone_and_target_neutral():
    p=export()
    assert p["schema"]=="midra.property.analysis.export"
    assert p["integration_target"] is None

def test_property_export_contract_is_versioned():
    assert export()["schema_version"]=="1.0"

def test_property_can_target_company_other_than_midra_engineering():
    p=property_export_for_external_company(
        export_payload=export(),company_integration_id="COMPANY-B")
    assert p["integration_target"]=="COMPANY-B"

def test_midra_engineering_can_exist_without_property():
    r=create_engineering_intake(request_id="REQ-2",source="PHONE",
        property_address="25 Main Street",requested_work="Plot plan addition")
    assert r["source"]=="PHONE" and r["external_reference"] is None

def test_property_handoff_is_optional_adapter_not_core_dependency():
    r=property_export_to_engineering(export_payload=export(),request_id="REQ-1")
    assert r["source"]=="MIDRA_PROPERTY"
    assert r["external_reference"]=="PA-77"
    assert r["imported_fields"]["block"]=="39.05"

def test_engineering_can_accept_non_property_external_integration():
    r=engineering_accept_external_payload(
        request_id="REQ-X",property_address="1 Main Street",
        requested_work="Site plan",provider_reference="CRM-44",
        fields={"client_name":"Example Client"})
    assert r["source"]=="EXTERNAL_INTEGRATION"
    assert r["external_reference"]=="CRM-44"

def test_property_export_does_not_contain_engineering_job_state():
    p=export()
    assert "job_number" not in p
    assert "engineering_workflow" not in p

def test_boundary_policy_explicitly_preserves_independent_products():
    p=product_boundary_policy()
    assert p["midra_property_is_independent_product"]
    assert p["midra_engineering_is_independent_product"]
    assert p["property_can_integrate_with_other_companies"]
