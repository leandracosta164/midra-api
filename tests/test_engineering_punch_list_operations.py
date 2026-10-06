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
    return SimpleNamespace(job_number="ENG-P2",project_name="Punch Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=18,sections={},events=[])

def test_create_progress_verify_and_close_punch_item():
    j=job();r=repo_for(j)
    r.add_punch_item(job_number=j.job_number,title="Repair wall finish",
        description="Patch and refinish damaged wall surface.",location="Room 101",
        responsible_party="GC",priority="HIGH",authorized_by="Leandra")
    pid=j.sections["punch_list"]["summary"]["items"][0]["punch_id"]
    assert engineering_workspace(j)["punch_list"]["open_count"]==1
    r.update_punch_item(job_number=j.job_number,punch_id=pid,status="READY_FOR_VERIFICATION",
        resolution_notes="Contractor reports repair complete.",authorized_by="Leandra")
    assert engineering_workspace(j)["punch_list"]["verification_count"]==1
    r.update_punch_item(job_number=j.job_number,punch_id=pid,status="CLOSED",
        resolution_notes="Repair verified complete.",authorized_by="Leandra")
    assert engineering_workspace(j)["punch_list"]["closed_count"]==1

def test_close_requires_resolution_notes():
    j=job();r=repo_for(j)
    r.add_punch_item(job_number=j.job_number,title="X",description="Y",authorized_by="Leandra")
    pid=j.sections["punch_list"]["summary"]["items"][0]["punch_id"]
    try:r.update_punch_item(job_number=j.job_number,punch_id=pid,status="CLOSED",authorized_by="Leandra")
    except ValueError as exc: assert "resolution notes" in str(exc)
    else: raise AssertionError("punch item closed without resolution notes")

def test_invalid_priority_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_punch_item(job_number=j.job_number,title="X",description="Y",priority="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "priority" in str(exc)
    else: raise AssertionError("invalid punch priority accepted")
