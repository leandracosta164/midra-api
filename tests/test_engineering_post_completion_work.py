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
    return SimpleNamespace(job_number="ENG-PCW",project_name="Post Completion",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections=sections or {},events=[])

def reopened_job():
    j=job();r=repo_for(j)
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Complete.",authorized_by="Leandra")
    r.reopen_completed_project(job_number=j.job_number,reason="Additional authorized work.",authorized_by="Leandra")
    return j,r

def test_post_completion_work_requires_reopened_project():
    j=job();r=repo_for(j)
    try:r.add_post_completion_work(job_number=j.job_number,title="Correction",description="Revise record.",
        authorized_by="Leandra")
    except ValueError as exc: assert "explicitly reopened" in str(exc)
    else: raise AssertionError("post-completion work added without reopening")

def test_post_completion_work_open_and_resolve_cycle():
    j,r=reopened_job()
    r.add_post_completion_work(job_number=j.job_number,title="Client revision",work_type="CLIENT_REQUEST",
        description="Document requested post-completion revision.",authorized_by="Leandra")
    w=engineering_workspace(j)["post_completion_work"]
    assert w["open_count"]==1 and w["items"][0]["status"]=="OPEN"
    item_id=w["items"][0]["item_id"]
    r.update_post_completion_work(job_number=j.job_number,item_id=item_id,status="RESOLVED",
        resolution_notes="Revision completed and reviewed.",authorized_by="Leandra")
    w=engineering_workspace(j)["post_completion_work"]
    assert w["open_count"]==0 and w["items"][0]["status"]=="RESOLVED"
    assert j.events[-1]["event_type"]=="POST_COMPLETION_WORK_STATUS_CHANGED"

def test_resolved_post_completion_work_requires_notes():
    j,r=reopened_job()
    r.add_post_completion_work(job_number=j.job_number,title="Correction",description="Correction required.",
        authorized_by="Leandra")
    item_id=j.sections["post_completion_work"]["summary"]["items"][0]["item_id"]
    try:r.update_post_completion_work(job_number=j.job_number,item_id=item_id,status="RESOLVED",
        resolution_notes="",authorized_by="Leandra")
    except ValueError as exc: assert "requires resolution notes" in str(exc)
    else: raise AssertionError("post-completion work resolved without notes")

def test_recertification_blocked_until_post_completion_work_resolved():
    j,r=reopened_job()
    r.add_post_completion_work(job_number=j.job_number,title="Correction",description="Correction required.",
        authorized_by="Leandra")
    try:r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-23",
        certification_notes="Attempt.",authorized_by="Leandra")
    except ValueError as exc: assert "post-completion work" in str(exc)
    else: raise AssertionError("re-certified with unresolved post-completion work")
    item_id=j.sections["post_completion_work"]["summary"]["items"][0]["item_id"]
    r.update_post_completion_work(job_number=j.job_number,item_id=item_id,status="RESOLVED",
        resolution_notes="Completed.",authorized_by="Leandra")
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-23",
        certification_notes="Additional work complete.",authorized_by="Leandra")
    assert engineering_workspace(j)["project_completion"]["certified"] is True
