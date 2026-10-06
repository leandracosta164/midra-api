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
    return SimpleNamespace(job_number="ENG-ACK",project_name="Audit Ack",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections={},events=[])

def test_acknowledgement_records_point_in_time_audit_snapshot():
    j=job();r=repo_for(j)
    r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="Reviewed lifecycle audit record.",acknowledged_by="Leandra")
    w=engineering_workspace(j)["lifecycle_audit"]
    assert w["acknowledgement_count"]==1
    ack=w["latest_acknowledgement"]
    assert ack["acknowledged_by"]=="Leandra"
    assert ack["audit_snapshot"]=={"completion_status":"NOT_CERTIFIED","certification_count":0,
                                   "reopen_count":0,"post_completion_open_count":0}
    assert j.events[-1]["event_type"]=="PROJECT_LIFECYCLE_AUDIT_ACKNOWLEDGED"

def test_acknowledgement_requires_notes():
    j=job();r=repo_for(j)
    try:r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="   ",acknowledged_by="Leandra")
    except ValueError as exc: assert "requires notes" in str(exc)
    else: raise AssertionError("audit acknowledgement accepted without notes")

def test_acknowledgement_does_not_change_lifecycle_decisions():
    j=job();r=repo_for(j)
    before=engineering_workspace(j)["lifecycle_audit"]["completion_status"]
    r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="Record reviewed.",acknowledged_by="Leandra")
    after=engineering_workspace(j)["lifecycle_audit"]["completion_status"]
    assert before=="NOT_CERTIFIED" and after=="NOT_CERTIFIED"
    assert "project_completion" not in j.sections
    assert "post_completion_work" not in j.sections

def test_repository_audit_includes_acknowledgement_history():
    j=job();r=repo_for(j)
    r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="First review.",acknowledged_by="Leandra")
    audit=r.project_lifecycle_audit(job_number=j.job_number)
    assert len(audit["acknowledgements"])==1
    assert audit["acknowledgements"][0]["acknowledgement_notes"]=="First review."
    assert audit["lifecycle_events"][-1]["event_type"]=="PROJECT_LIFECYCLE_AUDIT_ACKNOWLEDGED"
