from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self,job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository);r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r
def job():
    return SimpleNamespace(job_number="ENG-CO2",project_name="Change Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=18,sections={},events=[])

def test_create_approve_and_implement_change_order():
    j=job();r=repo_for(j)
    r.add_change_order(job_number=j.job_number,title="Revise foundation detail",
        description="Revise footing configuration at grid line 3.",requested_by="Contractor",
        cost_impact="$2,500",schedule_impact="2 days",authorized_by="Leandra")
    cid=j.sections["change_orders"]["summary"]["items"][0]["change_id"]
    assert engineering_workspace(j)["change_orders"]["pending_count"]==1
    r.update_change_order(job_number=j.job_number,change_id=cid,status="APPROVED",
        decision_notes="Approved following engineering review.",decided_by="Engineer",authorized_by="Leandra")
    assert engineering_workspace(j)["change_orders"]["approved_count"]==1
    r.update_change_order(job_number=j.job_number,change_id=cid,status="IMPLEMENTED",
        decision_notes="Implemented in issued construction revision.",authorized_by="Leandra")
    assert engineering_workspace(j)["change_orders"]["implemented_count"]==1

def test_final_change_order_status_requires_notes():
    j=job();r=repo_for(j)
    r.add_change_order(job_number=j.job_number,title="X",description="Y",authorized_by="Leandra")
    cid=j.sections["change_orders"]["summary"]["items"][0]["change_id"]
    try:r.update_change_order(job_number=j.job_number,change_id=cid,status="APPROVED",authorized_by="Leandra")
    except ValueError as exc: assert "decision notes" in str(exc)
    else: raise AssertionError("final change-order status accepted without notes")

def test_invalid_change_order_status_fails_closed():
    j=job();r=repo_for(j)
    r.add_change_order(job_number=j.job_number,title="X",description="Y",authorized_by="Leandra")
    cid=j.sections["change_orders"]["summary"]["items"][0]["change_id"]
    try:r.update_change_order(job_number=j.job_number,change_id=cid,status="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "status" in str(exc)
    else: raise AssertionError("invalid change-order status accepted")
