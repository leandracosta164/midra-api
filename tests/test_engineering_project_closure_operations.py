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
    return SimpleNamespace(job_number="ENG-C2",project_name="Closure Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=19,sections={},events=[])

def test_create_review_and_complete_closure_item():
    j=job();r=repo_for(j)
    r.add_project_closure_item(job_number=j.job_number,title="Final consultant invoice",
        closure_type="FINAL_INVOICE",responsible_party="Project manager",authorized_by="Leandra")
    cid=j.sections["project_closure"]["summary"]["items"][0]["closure_id"]
    assert engineering_workspace(j)["project_closure"]["open_count"]==1
    r.update_project_closure_item(job_number=j.job_number,closure_id=cid,status="READY_FOR_REVIEW",
        authorized_by="Leandra")
    assert engineering_workspace(j)["project_closure"]["review_count"]==1
    r.update_project_closure_item(job_number=j.job_number,closure_id=cid,status="COMPLETE",
        completion_notes="Final invoice reviewed and administrative closeout completed.",
        authorized_by="Leandra")
    assert engineering_workspace(j)["project_closure"]["complete_count"]==1

def test_final_closure_status_requires_completion_notes():
    j=job();r=repo_for(j)
    r.add_project_closure_item(job_number=j.job_number,title="Client acceptance",
        closure_type="CLIENT_ACCEPTANCE",authorized_by="Leandra")
    cid=j.sections["project_closure"]["summary"]["items"][0]["closure_id"]
    try:r.update_project_closure_item(job_number=j.job_number,closure_id=cid,status="COMPLETE",
        authorized_by="Leandra")
    except ValueError as exc: assert "completion notes" in str(exc)
    else: raise AssertionError("closure item completed without notes")

def test_invalid_closure_type_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_project_closure_item(job_number=j.job_number,title="X",closure_type="MAGIC",
        authorized_by="Leandra")
    except ValueError as exc: assert "closure item type" in str(exc)
    else: raise AssertionError("invalid closure type accepted")
