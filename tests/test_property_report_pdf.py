from app.services.property_report_pdf import render_property_report_pdf,verify_property_report_pdf

def bundle():
 return {"status":"PROPERTY_DELIVERY_READY","analysis_id":"a1","customer_report_profile":"COMPLETE","project_goal":"mixed-use redevelopment","property_record":{"property_record_id":"p1","address":"123 Main Street","municipality":"Example City","county":"Example County","block":"10","lot":"5"},"analysis_snapshot":{"zoning":{"district":"R-3"}},"master_evidence_package":{"screening_evidence":{"wetlands":{"screening":{"status":"VERIFY"}},"flood":{"screening":{"status":"NO_MAPPED_INTERSECTION"}}},"zoning_candidate_evidence":{"candidate_only":True,"candidate":{"record":{"zoning_district":"R-3"}}},"dynamic_intelligence_evidence":{"dynamic_promotable":False,"zoning":{"candidate":{"record":{"zoning_district":"R-3"}},"promotion":{"status":"VERIFY","reason":"SOURCE_AUTHORITY_NOT_CONFIRMED"}},"project_applicability":{"status":"VERIFY"},"approval_pathway_candidate":{"primary_pathway":"SITE_PLAN_APPROVAL","reviewing_bodies":["PLANNING_BOARD"]},"approval_pathway":{"status":"VERIFY"}},"verification_summary":{"items":["Verify controlling zoning source.","Wetlands review required."]},"sources":[{"label":"Municipal zoning map","source_url":"https://example.gov/zoning","authority_tier":"MUNICIPAL"}]},"customer_report":{"report_profile":"COMPLETE","sections":{"source_index":True,"verification_summary":True}},"professional_boundary":{"notice":"Delivery does not constitute engineer review or acceptance."}}

def test_pdf_report_integrity_and_sections():
 r=render_property_report_pdf(delivery_bundle=bundle())
 assert r["pdf_bytes"].startswith(b"%PDF-")
 assert b"MIDRA Property Intelligence Report" in r["pdf_bytes"]
 assert b"SITE_PLAN_APPROVAL" in r["pdf_bytes"]
 assert b"Professional Boundary" in r["pdf_bytes"]
 assert verify_property_report_pdf(rendered=r) is True

def test_verify_state_is_not_promoted():
 r=render_property_report_pdf(delivery_bundle=bundle())
 assert b"VERIFY / candidate context" in r["pdf_bytes"]
 assert b"SOURCE_AUTHORITY_NOT_CONFIRMED" in r["pdf_bytes"]
 assert r["professional_boundary"]["engineer_reviewed"] is False
