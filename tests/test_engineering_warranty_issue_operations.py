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
    return SimpleNamespace(job_number="ENG-W2",project_name="Warranty Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=19,sections={},events=[])

def test_create_verify_and_resolve_warranty_issue():
    j=job();r=repo_for(j)
    r.add_warranty_issue(job_number=j.job_number,title="Door closer failure",
        description="Closer is leaking and no longer controls door.",location="Lobby",
        responsible_party="Door supplier",priority="HIGH",authorized_by="Leandra")
    iid=j.sections["warranty_issues"]["summary"]["items"][0]["issue_id"]
    assert engineering_workspace(j)["warranty_issues"]["open_count"]==1
    r.update_warranty_issue(job_number=j.job_number,issue_id=iid,status="READY_FOR_VERIFICATION",
        resolution_notes="Replacement closer installed.",authorized_by="Leandra")
    assert engineering_workspace(j)["warranty_issues"]["verification_count"]==1
    r.update_warranty_issue(job_number=j.job_number,issue_id=iid,status="RESOLVED",
        resolution_notes="Replacement verified operational.",authorized_by="Leandra")
    assert engineering_workspace(j)["warranty_issues"]["resolved_count"]==1

def test_resolution_requires_notes():
    j=job();r=repo_for(j)
    r.add_warranty_issue(job_number=j.job_number,title="X",description="Y",authorized_by="Leandra")
    iid=j.sections["warranty_issues"]["summary"]["items"][0]["issue_id"]
    try:r.update_warranty_issue(job_number=j.job_number,issue_id=iid,status="RESOLVED",authorized_by="Leandra")
    except ValueError as exc: assert "resolution notes" in str(exc)
    else: raise AssertionError("warranty issue resolved without notes")

def test_invalid_priority_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_warranty_issue(job_number=j.job_number,title="X",description="Y",priority="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "priority" in str(exc)
    else: raise AssertionError("invalid warranty priority accepted")
