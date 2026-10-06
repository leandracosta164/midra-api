from app.services.property_engineering_intake_bridge import build_property_engineering_intake_bridge

def proposal():
    return {
        "proposal_request_id":"pr-1",
        "property_record_id":"p-1",
        "analysis_run_id":"a-1",
        "project_goal":"mixed-use redevelopment",
        "customer_name":"Jane Client",
        "customer_email":"jane@example.com",
        "customer_phone":"555-0100",
        "request_status":"REQUESTED",
    }

def property_record():
    return {
        "property_record_id":"p-1",
        "address":"123 Main Street",
        "municipality":"Example City",
        "county":"Example County",
        "block":"10","lot":"5",
    }

def test_bridge_builds_engineering_workspace_without_job_creation():
    result=build_property_engineering_intake_bridge(
        proposal_request=proposal(),
        property_record=property_record(),
        analysis_id="a-1",
        analysis_snapshot={"project_goal":"mixed-use redevelopment"},
        evidence_package={"artifacts":[],"verification_summary":{"status":"VERIFICATION_REQUIRED"}},
        engineering_user="engineer@midra.local",
    )
    assert result["status"]=="ENGINEERING_PROPERTY_PROPOSAL_INTAKE_READY"
    assert result["source_product"]=="MIDRA_PROPERTY"
    assert result["intake"]["status"]=="NEW_PROPOSAL_REQUEST"
    assert result["workspace"]["status"]=="ENGINEERING_WORKSPACE_READY"
    assert result["workspace"]["shared_platform_reference"]["analysis_id"]=="a-1"
    assert result["workspace"]["duplicate_property_research_required"] is False
    assert result["proposal"]["status"]=="NOT_GENERATED"
    assert result["professional_boundary"]["engineering_job_created"] is False

def test_bridge_rejects_analysis_substitution():
    item=proposal(); item["analysis_run_id"]="a-original"
    try:
        build_property_engineering_intake_bridge(
            proposal_request=item,property_record=property_record(),
            analysis_id="a-latest",analysis_snapshot={},evidence_package={},
            engineering_user="engineer@midra.local",
        )
    except ValueError as exc:
        assert "exact Property analysis" in str(exc)
    else:
        raise AssertionError("analysis substitution should be rejected")

def test_bridge_requires_engineering_identity():
    try:
        build_property_engineering_intake_bridge(
            proposal_request=proposal(),property_record=property_record(),
            analysis_id="a-1",analysis_snapshot={},evidence_package={},
            engineering_user="",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Engineering identity must be required")
