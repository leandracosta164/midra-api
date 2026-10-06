from app.services.property_report_pdf import _report_lines, render_property_report_pdf, verify_property_report_pdf


def _bundle():
    return {
        "status": "PROPERTY_DELIVERY_READY",
        "analysis_id": "a236",
        "customer_report_profile": "COMPLETE",
        "property_record": {"address": "1 Main Street", "municipality": "Howell", "county": "Monmouth", "block": "145", "lot": "22"},
        "analysis_snapshot": {},
        "master_evidence_package": {
            "screening_evidence": {
                "wetlands": {"screening": {"screening_result": "MAPPED_INTERSECTION", "source": {
                    "agency": "New Jersey Department of Environmental Protection",
                    "dataset": "Wetlands (2012)",
                    "url": "https://mapsdep.nj.gov/example/wetlands",
                    "current_status": "VERIFY_CURRENTNESS",
                    "retrieved_at": "2026-10-04T12:00:00Z",
                    "last_checked_at": "2026-10-04T12:00:00Z",
                    "currentness_note": "Current applicability requires verification before professional reliance.",
                }}},
                "flood": {"screening": {"screening_result": "NO_MAPPED_INTERSECTION", "source": {
                    "agency": "FEMA / New Jersey Department of Environmental Protection",
                    "dataset": "National Flood Hazard Layer (NFHL)",
                    "url": "https://mapsdep.nj.gov/example/flood",
                    "current_status": "VERIFY_CURRENTNESS",
                    "retrieved_at": "2026-10-04T12:05:00Z",
                    "last_checked_at": "2026-10-04T12:05:00Z",
                    "currentness_note": "Current FEMA/NJDEP applicability requires verification before professional reliance.",
                }}},
            },
            "verification_summary": {"items": []},
            "sources": [],
        },
        "customer_report": {"sections": {"environmental_screening": True}},
        "professional_boundary": {"notice": "Research and screening only."},
    }


def _text_lines():
    return [row["text"] for row in _report_lines(_bundle())]


def test_report_lines_carry_environmental_source_currentness_and_retrieval_context():
    joined=" ".join(_text_lines())
    for expected in (
        "Wetlands source: Wetlands (2012)",
        "Wetlands source URL: https://mapsdep.nj.gov/example/wetlands",
        "Wetlands source currentness: VERIFY_CURRENTNESS",
        "Wetlands source retrieved: 2026-10-04T12:00:00Z",
        "Flood source: National Flood Hazard Layer (NFHL)",
        "Flood source URL: https://mapsdep.nj.gov/example/flood",
        "Flood source currentness: VERIFY_CURRENTNESS",
        "Flood source retrieved: 2026-10-04T12:05:00Z",
        "verification before professional reliance",
    ):
        assert expected in joined


def test_pdf_integrity_and_professional_boundary_are_preserved():
    rendered=render_property_report_pdf(delivery_bundle=_bundle())
    assert rendered["pdf_bytes"].startswith(b"%PDF-")
    assert verify_property_report_pdf(rendered=rendered) is True
    joined=" ".join(_text_lines())
    assert "reference/screening evidence" in joined
    assert "VERIFY conditions remain unresolved" in joined
