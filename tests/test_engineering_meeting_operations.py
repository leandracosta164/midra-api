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
    return SimpleNamespace(job_number="ENG-MTG2",project_name="Meeting Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=17,sections={},events=[])

def test_create_and_complete_meeting():
    j=job();r=repo_for(j)
    r.add_meeting(job_number=j.job_number,title="Client coordination",meeting_type="CLIENT",
        attendees=["Client","PM"],authorized_by="Leandra")
    mid=j.sections["meetings"]["summary"]["items"][0]["meeting_id"]
    assert engineering_workspace(j)["meetings"]["scheduled_count"]==1
    r.update_meeting(job_number=j.job_number,meeting_id=mid,status="COMPLETED",
        notes="Minutes recorded",authorized_by="Leandra")
    assert engineering_workspace(j)["meetings"]["completed_count"]==1
    assert j.events[-1]["event_type"]=="MEETING_STATUS_CHANGED"

def test_invalid_meeting_status_fails_closed():
    j=job();r=repo_for(j);r.add_meeting(job_number=j.job_number,title="X",authorized_by="Leandra")
    mid=j.sections["meetings"]["summary"]["items"][0]["meeting_id"]
    try:r.update_meeting(job_number=j.job_number,meeting_id=mid,status="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "status" in str(exc)
    else: raise AssertionError("invalid meeting status accepted")
