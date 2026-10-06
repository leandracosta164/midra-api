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
def job(sections=None):
    return SimpleNamespace(job_number="ENG-REOPEN",project_name="Reopen",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections=sections or {},events=[])

def certified_job():
    j=job();r=repo_for(j)
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Final obligations reviewed.",authorized_by="Leandra")
    return j,r

def test_certified_project_can_be_explicitly_reopened():
    j,r=certified_job()
    r.reopen_completed_project(job_number=j.job_number,reason="Post-completion client-directed work.",
        authorized_by="Leandra")
    c=engineering_workspace(j)["project_completion"]
    assert c["certified"] is False and c["reopened"] is True
    assert c["certification"]["status"]=="REOPENED"
    assert c["certification"]["reopen_reason"]=="Post-completion client-directed work."
    assert c["reopen_history"][-1]["authorized_by"]=="Leandra"
    assert j.events[-1]["event_type"]=="PROJECT_REOPENED_AFTER_COMPLETION"

def test_uncertified_project_cannot_be_reopened():
    j=job();r=repo_for(j)
    try:r.reopen_completed_project(job_number=j.job_number,reason="No certification.",authorized_by="Leandra")
    except ValueError as exc: assert "certified project" in str(exc)
    else: raise AssertionError("uncertified project reopened")

def test_reopen_requires_reason():
    j,r=certified_job()
    try:r.reopen_completed_project(job_number=j.job_number,reason="   ",authorized_by="Leandra")
    except ValueError as exc: assert "requires a reason" in str(exc)
    else: raise AssertionError("project reopened without reason")

def test_reopened_project_can_be_recertified_with_history_preserved():
    j,r=certified_job()
    first=j.sections["project_completion"]["summary"]["certification"]["certification_id"]
    r.reopen_completed_project(job_number=j.job_number,reason="Additional closeout work.",authorized_by="Leandra")
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-23",
        certification_notes="Additional work reviewed and complete.",authorized_by="Leandra")
    summary=j.sections["project_completion"]["summary"]
    assert summary["certification"]["status"]=="CERTIFIED"
    assert summary["certification"]["certification_id"]!=first
    assert summary["certification_history"][-1]["certification_id"]==first
    assert summary["certification_history"][-1]["status"]=="REOPENED"
