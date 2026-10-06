import sys, types
stub=types.ModuleType("app.db.session")
stub.get_db=lambda: None
sys.modules["app.db.session"]=stub

from app.api.property_records import _build_public_report_bundle, create_public_property_delivery_report_pdf
from app.schemas.property_record import PropertyPublicReportCreate
from app.services.property_report_pdf import verify_property_report_pdf, render_property_report_pdf


def analysis():
    return {
        "property":{"address":"123 Main Street","municipality":"Example City","county":"Example County","parcel":{"block":"10","lot":"5"}},
        "project_goal":"mixed-use redevelopment",
        "zoning":{"district":"R-3"},
        "verification_items":["Verify controlling zoning source."],
        "dynamic_intelligence":{"dynamic_promotable":False,"zoning":{"promotion":{"status":"VERIFY","promotable":False,"reason":"SOURCE_AUTHORITY_NOT_CONFIRMED"}}},
    }


def payload(profile="preliminary"):
    return PropertyPublicReportCreate(search_query="123 Main Street",analysis=analysis(),project_goal="mixed-use redevelopment",report_profile=profile)


def test_public_report_bundle_is_browser_only_and_non_professional():
    bundle=_build_public_report_bundle(payload())
    assert bundle["product"]=="MIDRA_PROPERTY"
    assert bundle["public_browser_export"] is True
    assert bundle["property_record"]["municipality"]=="Example City"
    assert bundle["analysis_id"].startswith("PUBLIC-")
    assert bundle["professional_boundary"]["engineer_reviewed"] is False
    assert bundle["professional_boundary"]["engineer_accepted"] is False


def test_public_report_renders_real_pdf_without_durable_record():
    bundle=_build_public_report_bundle(payload("complete"))
    rendered=render_property_report_pdf(delivery_bundle=bundle)
    assert rendered["pdf_bytes"].startswith(b"%PDF-")
    assert verify_property_report_pdf(rendered=rendered) is True
    response=create_public_property_delivery_report_pdf(payload("complete"))
    assert response.media_type=="application/pdf"
    assert response.body.startswith(b"%PDF-")
    assert response.headers["x-midra-persistence"]=="browser-only"


def test_public_report_requires_resolved_municipality():
    from fastapi import HTTPException
    p=PropertyPublicReportCreate(search_query="Unknown property",analysis={"property":{"address":"Unknown property"}},report_profile="preliminary")
    try:
        _build_public_report_bundle(p)
    except HTTPException as exc:
        assert exc.status_code==422
        assert "resolved municipality" in str(exc.detail)
    else:
        raise AssertionError("expected resolved municipality requirement")


def test_public_report_profile_is_guarded():
    from fastapi import HTTPException
    try:
        _build_public_report_bundle(payload("secret"))
    except HTTPException as exc:
        assert exc.status_code==422
    else:
        raise AssertionError("expected report profile validation")
