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
    return SimpleNamespace(job_number="ENG-M2",project_name="Milestone Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=16,sections={},events=[])

def test_create_and_complete_milestone():
    j=job();r=repo_for(j)
    r.add_milestone(job_number=j.job_number,title="Permit submission",milestone_type="PERMIT",
        due_at="2026-10-01",owner="PM",authorized_by="Leandra")
    mid=j.sections["milestones"]["summary"]["items"][0]["milestone_id"]
    assert engineering_workspace(j)["milestones"]["open_count"]==1
    r.update_milestone(job_number=j.job_number,milestone_id=mid,status="COMPLETE",
        notes="Completed",authorized_by="Leandra")
    assert engineering_workspace(j)["milestones"]["complete_count"]==1
    assert j.events[-1]["event_type"]=="MILESTONE_STATUS_CHANGED"

def test_invalid_milestone_status_fails_closed():
    j=job();r=repo_for(j)
    r.add_milestone(job_number=j.job_number,title="X",authorized_by="Leandra")
    mid=j.sections["milestones"]["summary"]["items"][0]["milestone_id"]
    try:r.update_milestone(job_number=j.job_number,milestone_id=mid,status="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "status" in str(exc)
    else: raise AssertionError("invalid milestone status accepted")
