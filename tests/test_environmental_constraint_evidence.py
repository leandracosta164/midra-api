from app.services.environmental_constraint_evidence import build_environmental_constraint_evidence

def test_environmental_constraints_do_not_invent_property_findings():
    result=build_environmental_constraint_evidence(property_resolution={"status":"PROPERTY_RESOLVED"})
    assert result["status"]=="NOT_EVALUATED"
    for key in ("flood","wetlands"):
        item=result[key]
        assert item["status"]=="NOT_EVALUATED"
        assert item["evidence_available"] is False
        assert item["source"] is None
        assert item["verification_required"] is True

def test_unresolved_property_remains_not_evaluated():
    result=build_environmental_constraint_evidence(property_resolution={"status":"ADDRESS_NOT_RESOLVED"})
    assert result["parcel_resolved"] is False
    assert result["flood"]["status"]=="NOT_EVALUATED"
    assert result["wetlands"]["status"]=="NOT_EVALUATED"
