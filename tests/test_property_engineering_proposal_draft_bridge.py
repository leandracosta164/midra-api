from app.services.property_engineering_proposal_draft_bridge import build_property_engineering_proposal_draft

def intake_bridge():
    return {
        "status":"ENGINEERING_PROPERTY_PROPOSAL_INTAKE_READY",
        "property_proposal_request_id":"pr-1",
        "intake":{
            "status":"NEW_PROPOSAL_REQUEST",
            "request_id":"MER-1",
            "project_goal":"mixed-use redevelopment",
            "customer":{"name":"Jane Client","email":"jane@example.com"},
            "shared_platform_reference":{"property_record_id":"p-1","analysis_id":"a-1","analysis_snapshot_id":"a-1"},
        },
        "workspace":{
            "status":"ENGINEERING_WORKSPACE_READY",
            "project_goal":"mixed-use redevelopment",
            "customer":{"name":"Jane Client","email":"jane@example.com"},
            "property_record":{"property_record_id":"p-1","address":"123 Main Street"},
            "shared_platform_reference":{"property_record_id":"p-1","analysis_id":"a-1","analysis_snapshot_id":"a-1"},
        },
    }

def test_builds_private_review_required_draft_with_exact_lineage():
    draft=build_property_engineering_proposal_draft(
        intake_bridge=intake_bridge(), engineering_user="engineer@midra.local",
        proposal_number="P-2026-001", proposal_date="2026-10-03",
        services=[{"service":"Conceptual Site Plan","price":"2500"}],
        exclusions=["Surveying unless separately authorized"],
        terms=["30-day proposal validity"],
    )
    assert draft["status"]=="DRAFT_REQUIRES_ENGINEER_REVIEW"
    assert draft["total_price"]=="2500.00"
    assert draft["property_record_id"]=="p-1"
    assert draft["analysis_id"]=="a-1"
    assert draft["property_proposal_request_id"]=="pr-1"
    assert draft["pricing_source"]=="ENGINEERING_EXPLICIT_INPUT"
    assert draft["send_allowed"] is False
    assert draft["engineering_job_created"] is False
    assert draft["professional_boundary"]["engineer_reviewed"] is False

def test_refuses_missing_explicit_price():
    try:
        build_property_engineering_proposal_draft(
            intake_bridge=intake_bridge(),engineering_user="engineer@midra.local",
            proposal_number="P-1",proposal_date="2026-10-03",
            services=[{"service":"Site Plan"}],
        )
    except ValueError as exc:
        assert "price is required" in str(exc)
    else:
        raise AssertionError("missing price must fail")

def test_refuses_non_engineering_intake_state():
    bad=intake_bridge(); bad["status"]="VERIFY"
    try:
        build_property_engineering_proposal_draft(
            intake_bridge=bad,engineering_user="engineer@midra.local",
            proposal_number="P-1",proposal_date="2026-10-03",
            services=[{"service":"Site Plan","price":"1000"}],
        )
    except ValueError as exc:
        assert "exact Engineering Property intake" in str(exc)
    else:
        raise AssertionError("invalid intake must fail")

def test_requires_engineering_identity():
    try:
        build_property_engineering_proposal_draft(
            intake_bridge=intake_bridge(),engineering_user="",
            proposal_number="P-1",proposal_date="2026-10-03",
            services=[{"service":"Site Plan","price":"1000"}],
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Engineering identity must be required")
