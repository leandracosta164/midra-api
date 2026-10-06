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
    return SimpleNamespace(job_number="ENG-S2",project_name="Submittal Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=17,sections={},events=[])

def test_create_review_and_close_submittal():
    j=job();r=repo_for(j)
    r.add_submittal(job_number=j.job_number,title="Structural steel shop drawings",
        submittal_type="SHOP_DRAWING",submitted_by="Contractor",authorized_by="Leandra")
    sid=j.sections["submittals"]["summary"]["items"][0]["submittal_id"]
    assert engineering_workspace(j)["submittals"]["pending_count"]==1
    r.review_submittal(job_number=j.job_number,submittal_id=sid,status="APPROVED_AS_NOTED",
        review_notes="Approved as noted on reviewed sheets.",reviewed_by="Engineer",authorized_by="Leandra")
    assert engineering_workspace(j)["submittals"]["approved_count"]==1
    r.review_submittal(job_number=j.job_number,submittal_id=sid,status="CLOSED",
        review_notes="Review cycle complete.",authorized_by="Leandra")
    assert engineering_workspace(j)["submittals"]["closed_count"]==1

def test_final_review_status_requires_notes():
    j=job();r=repo_for(j)
    r.add_submittal(job_number=j.job_number,title="X",authorized_by="Leandra")
    sid=j.sections["submittals"]["summary"]["items"][0]["submittal_id"]
    try:r.review_submittal(job_number=j.job_number,submittal_id=sid,status="APPROVED",authorized_by="Leandra")
    except ValueError as exc: assert "review notes" in str(exc)
    else: raise AssertionError("final submittal review accepted without notes")

def test_invalid_submittal_type_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_submittal(job_number=j.job_number,title="X",submittal_type="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "type" in str(exc)
    else: raise AssertionError("invalid submittal type accepted")
