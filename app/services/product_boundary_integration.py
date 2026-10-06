"""Phase 5.78 — independent-product boundary and optional integration contract.

MIDRA Property and MIDRA Engineering are independent products. Neither product's core
operation depends on the other. Cross-product exchange occurs only through explicit,
versioned integration payloads/adapters.
"""

ENGINEERING_SOURCES={
    "MANUAL","PHONE","EMAIL","ENGINEERING_WEBSITE","MIDRA_PROPERTY","EXTERNAL_INTEGRATION"
}

def create_engineering_intake(*, request_id, source, property_address, requested_work,
                              external_reference=None, imported_fields=None):
    if source not in ENGINEERING_SOURCES:
        raise ValueError("unsupported engineering intake source")
    return {
        "request_id":request_id,
        "source":source,
        "property_address":property_address,
        "requested_work":requested_work,
        "external_reference":external_reference,
        "imported_fields":dict(imported_fields or {}),
        "status":"NEW",
    }

def create_property_export(*, analysis_id, property_address, requested_work,
                           analysis_fields, integration_target=None):
    """MIDRA Property export is target-neutral unless a target is explicitly selected."""
    return {
        "schema":"midra.property.analysis.export",
        "schema_version":"1.0",
        "analysis_id":analysis_id,
        "property_address":property_address,
        "requested_work":requested_work,
        "analysis_fields":dict(analysis_fields),
        "integration_target":integration_target,
    }

def property_export_to_engineering(*, export_payload, request_id):
    """Optional adapter. Engineering consumes a contract, not Property internals."""
    if export_payload.get("schema")!="midra.property.analysis.export":
        raise ValueError("unsupported property export schema")
    return create_engineering_intake(
        request_id=request_id,
        source="MIDRA_PROPERTY",
        property_address=export_payload["property_address"],
        requested_work=export_payload["requested_work"],
        external_reference=export_payload["analysis_id"],
        imported_fields=export_payload.get("analysis_fields",{}),
    )

def property_export_for_external_company(*, export_payload, company_integration_id):
    """Demonstrates that Property can integrate with companies other than MIDRA Engineering."""
    r=dict(export_payload)
    r["analysis_fields"]=dict(export_payload.get("analysis_fields",{}))
    r["integration_target"]=company_integration_id
    return r

def engineering_accept_external_payload(*, request_id, property_address, requested_work,
                                        provider_reference, fields):
    """Generic Engineering adapter independent of MIDRA Property."""
    return create_engineering_intake(
        request_id=request_id,source="EXTERNAL_INTEGRATION",
        property_address=property_address,requested_work=requested_work,
        external_reference=provider_reference,imported_fields=fields,
    )

def product_boundary_policy():
    return {
        "midra_property_is_independent_product":True,
        "midra_engineering_is_independent_product":True,
        "property_does_not_require_engineering":True,
        "engineering_does_not_require_property":True,
        "cross_product_handoff_is_optional":True,
        "integration_contract_is_versioned":True,
        "property_can_integrate_with_other_companies":True,
        "engineering_can_accept_other_integrations":True,
    }
