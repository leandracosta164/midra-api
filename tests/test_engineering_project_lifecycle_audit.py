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
    return SimpleNamespace(job_number="ENG-AUDIT",project_name="Audit",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections={},events=[])

def test_lifecycle_audit_preserves_completion_reopen_and_post_completion_record():
    j=job();r=repo_for(j)
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Initial completion.",authorized_by="Leandra")
    r.reopen_completed_project(job_number=j.job_number,reason="Authorized additional work.",authorized_by="Leandra")
    r.add_post_completion_work(job_number=j.job_number,title="Correction",work_type="CORRECTION",
        description="Complete post-project correction.",authorized_by="Leandra")
    item=j.sections["post_completion_work"]["summary"]["items"][0]
    r.update_post_completion_work(job_number=j.job_number,item_id=item["item_id"],status="RESOLVED",
        resolution_notes="Correction reviewed and resolved.",authorized_by="Leandra")
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-23",
        certification_notes="Reopened work resolved.",authorized_by="Leandra")
    audit=r.project_lifecycle_audit(job_number=j.job_number)
    assert audit["completion_certification"]["status"]=="CERTIFIED"
    assert len(audit["certification_history"])==1
    assert len(audit["reopen_history"])==1
    assert audit["post_completion_work"][0]["status"]=="RESOLVED"
    assert [e["event_type"] for e in audit["lifecycle_events"]]==[
        "PROJECT_COMPLETION_CERTIFIED","PROJECT_REOPENED_AFTER_COMPLETION",
        "POST_COMPLETION_WORK_OPENED","POST_COMPLETION_WORK_STATUS_CHANGED",
        "PROJECT_COMPLETION_CERTIFIED"]

def test_workspace_lifecycle_audit_is_derived_not_decisional():
    j=job();r=repo_for(j)
    w=engineering_workspace(j)["lifecycle_audit"]
    assert w["completion_status"]=="NOT_CERTIFIED"
    assert w["certification_count"]==0
    assert w["reopen_count"]==0
    assert w["post_completion_open_count"]==0
    assert j.sections=={} and j.events==[]
