from app.services.property_engineering_proposal_draft_bridge import build_property_engineering_proposal_draft
from app.services.property_engineering_proposal_review_bridge import approve_property_engineering_proposal_draft


def _bridge():
    return {
        "status":"ENGINEERING_PROPERTY_PROPOSAL_INTAKE_READY",
        "property_proposal_request_id":"pr-239",
        "intake":{
            "status":"NEW_PROPOSAL_REQUEST",
            "request_id":"MER-239",
            "project_goal":"mixed-use redevelopment",
            "customer":{"name":"Jane Client","email":"jane@example.com"},
            "shared_platform_reference":{"property_record_id":"p-239","analysis_id":"a-239","analysis_snapshot_id":"a-239"},
        },
        "workspace":{
            "status":"ENGINEERING_WORKSPACE_READY",
            "project_goal":"mixed-use redevelopment",
            "customer":{"name":"Jane Client","email":"jane@example.com"},
            "property_record":{"property_record_id":"p-239","address":"123 Main Street"},
            "shared_platform_reference":{"property_record_id":"p-239","analysis_id":"a-239","analysis_snapshot_id":"a-239"},
            "analysis":{
                "analysis_id":"a-239",
                "analysis_snapshot_id":"a-239",
                "analysis":{
                    "verification_items":[{"code":"VERIFY_ZONING","message":"Confirm controlling zoning source."}],
                    "dynamic_intelligence":{
                        "dynamic_promotable":False,
                        "source_trust_summary":{
                            "trust_state":"VERIFY",
                            "verification_required":True,
                            "official_representation":{"confirmed":True},
                            "legal_control":{"confirmed":False},
                            "source_currentness":{"current_status":"VERIFY","last_checked_at":"2026-10-04T12:00:00Z"},
                        },
                        "zoning":{"candidate":{"record":{"zoning_district":"R-1"}},"promotion":{"status":"VERIFY","reason":"LEGAL_CONTROL_NOT_CONFIRMED","promotable":False}},
                        "project_applicability":{"status":"VERIFY","reason":"VERIFY","promotable":False},
                        "approval_pathway":{"status":"VERIFY","primary_pathway":None,"reviewing_bodies":[],"reason":"VERIFY","promotable":False},
                    },
                },
            },
        },
    }


def test_property_intelligence_context_is_preserved_for_engineering_review():
    draft=build_property_engineering_proposal_draft(
        intake_bridge=_bridge(),engineering_user="engineer@midra.local",
        proposal_number="P-239",proposal_date="2026-10-04",
        services=[{"service":"Conceptual Site Plan","price":"2500"}],
    )
    context=draft["property_intelligence_context"]
    assert context["analysis_id"]=="a-239"
    assert context["verification_summary"]["status"]=="VERIFICATION_REQUIRED"
    assert context["dynamic_intelligence_summary"]["source_trust"]["trust_state"]=="VERIFY"
    assert context["dynamic_intelligence_summary"]["source_trust"]["authority_confirmed"] is True
    assert context["dynamic_intelligence_summary"]["source_trust"]["legal_control_confirmed"] is False
    assert context["professional_boundary"]["engineer_reviewed"] is False
    assert context["professional_boundary"]["engineer_accepted"] is False

    approved=approve_property_engineering_proposal_draft(
        draft_snapshot=draft,engineering_user="engineer@midra.local"
    )
    assert approved["property_intelligence_context"]==context
    assert approved["professional_boundary"]["proposal_engineer_approved"] is True
    assert approved["professional_boundary"]["property_analysis_engineer_accepted"] is False
