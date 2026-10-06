from app.services.zoning_evidence_promotion import evaluate_dynamic_zoning_promotion


def candidate(**source):
    return {"status": "ZONING_CANDIDATE_RESOLVED", "record": {"zoning_district": "R-60", "source": source}}


def test_missing_candidate_is_verify():
    r = evaluate_dynamic_zoning_promotion(None)
    assert r == {"status": "VERIFY", "promotable": False, "reason": "NO_DYNAMIC_CANDIDATE"}


def test_non_candidate_is_verify():
    r = evaluate_dynamic_zoning_promotion({"status": "ZONING_NOT_RESOLVED"})
    assert r["promotable"] is False
    assert r["reason"] == "CANDIDATE_NOT_RESOLVED"


def test_dynamic_gis_candidate_without_authority_is_verify():
    r = evaluate_dynamic_zoning_promotion(candidate(authoritative=False, legal_control_confirmed=False))
    assert r["status"] == "VERIFY"
    assert r["reason"] == "SOURCE_AUTHORITY_NOT_CONFIRMED"


def test_authority_without_legal_control_is_verify():
    r = evaluate_dynamic_zoning_promotion(candidate(authoritative=True, legal_control_confirmed=False))
    assert r["status"] == "VERIFY"
    assert r["reason"] == "LEGAL_CONTROL_NOT_CONFIRMED"


def test_explicit_authority_and_legal_control_promotes():
    r = evaluate_dynamic_zoning_promotion(candidate(authoritative=True, legal_control_confirmed=True))
    assert r["status"] == "ZONING_RESOLVED"
    assert r["promotable"] is True
    assert r["record"]["zoning_district"] == "R-60"


def test_missing_district_is_verify():
    r = evaluate_dynamic_zoning_promotion({"status": "ZONING_CANDIDATE_RESOLVED", "record": {"source": {"authoritative": True, "legal_control_confirmed": True}}})
    assert r["reason"] == "DISTRICT_MISSING"
