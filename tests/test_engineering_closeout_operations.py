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
    return SimpleNamespace(job_number="ENG-C2",project_name="Closeout Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=18,sections={},events=[])

def test_create_review_and_accept_closeout_item():
    j=job();r=repo_for(j)
    r.add_closeout_item(job_number=j.job_number,title="Record drawings",item_type="AS_BUILT",
        responsible_party="Contractor",authorized_by="Leandra")
    cid=j.sections["closeout"]["summary"]["items"][0]["closeout_id"]
    assert engineering_workspace(j)["closeout"]["open_count"]==1
    r.update_closeout_item(job_number=j.job_number,closeout_id=cid,status="READY_FOR_REVIEW",
        completion_notes="Record drawings uploaded for review.",authorized_by="Leandra")
    assert engineering_workspace(j)["closeout"]["review_count"]==1
    r.update_closeout_item(job_number=j.job_number,closeout_id=cid,status="ACCEPTED",
        completion_notes="Reviewed and accepted for project closeout.",authorized_by="Leandra")
    assert engineering_workspace(j)["closeout"]["accepted_count"]==1

def test_final_closeout_status_requires_notes():
    j=job();r=repo_for(j)
    r.add_closeout_item(job_number=j.job_number,title="Warranty",item_type="WARRANTY",authorized_by="Leandra")
    cid=j.sections["closeout"]["summary"]["items"][0]["closeout_id"]
    try:r.update_closeout_item(job_number=j.job_number,closeout_id=cid,status="ACCEPTED",authorized_by="Leandra")
    except ValueError as exc: assert "completion notes" in str(exc)
    else: raise AssertionError("closeout item accepted without completion notes")

def test_invalid_closeout_type_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_closeout_item(job_number=j.job_number,title="X",item_type="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "type" in str(exc)
    else: raise AssertionError("invalid closeout type accepted")
