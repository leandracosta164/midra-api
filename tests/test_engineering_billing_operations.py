from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r

def job():
    return SimpleNamespace(job_number="ENG-144",project_name="Billing Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=14,sections={},events=[])

def test_create_billing_record_flows_into_existing_register():
    j=job(); r=repo_for(j)
    r.add_billing_record(job_number=j.job_number,billing_type="INVOICE",reference="INV-001",
        status="ISSUED",issued_at="2026-09-20",due_at="2026-10-20",authorized_by="Leandra")
    w=engineering_workspace(j)
    assert w["billing"]["count"]==1
    assert w["billing"]["open_count"]==1
    assert w["billing"]["paid_count"]==0
    assert j.events[-1]["event_type"]=="BILLING_RECORD_CREATED"

def test_update_billing_status_to_paid():
    j=job(); r=repo_for(j)
    r.add_billing_record(job_number=j.job_number,billing_type="INVOICE",reference="INV-002",
        status="OPEN",authorized_by="Leandra")
    bid=j.sections["billing"]["summary"]["items"][0]["billing_id"]
    r.update_billing_status(job_number=j.job_number,billing_id=bid,status="PAID",
        notes="Payment recorded",authorized_by="Leandra")
    w=engineering_workspace(j)
    assert w["billing"]["open_count"]==0
    assert w["billing"]["paid_count"]==1
    assert j.events[-1]["event_type"]=="BILLING_STATUS_CHANGED"

def test_invalid_billing_status_fails_closed():
    j=job(); r=repo_for(j)
    try:
        r.add_billing_record(job_number=j.job_number,billing_type="INVOICE",reference="INV-X",
            status="MAGIC",authorized_by="Leandra")
    except ValueError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("invalid billing status was accepted")
