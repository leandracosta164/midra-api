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
    return SimpleNamespace(job_number="ENG-ACK-HISTORY",project_name="Audit Ack History",
        project_type="SITE",source="TEST",property_address="1 Project Way",client_id="CLIENT-1",
        state="ACTIVE",version=20,sections={},events=[])

def test_acknowledgement_history_is_read_only_and_preserves_record_order():
    j=job();r=repo_for(j)
    for note in ["First review.","Second review.","Third review."]:
        r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
            acknowledgement_notes=note,acknowledged_by="Leandra")
    before_sections=j.sections.copy();before_events=list(j.events)
    items=r.project_lifecycle_audit_acknowledgements(job_number=j.job_number)
    assert [x["acknowledgement_notes"] for x in items]==[
        "First review.","Second review.","Third review."]
    assert j.sections==before_sections and j.events==before_events

def test_workspace_exposes_bounded_recent_acknowledgement_history_newest_first():
    j=job();r=repo_for(j)
    for i in range(30):
        r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
            acknowledgement_notes=f"Review {i:02d}.",acknowledged_by="Leandra")
    w=engineering_workspace(j)["lifecycle_audit"]
    assert w["acknowledgement_count"]==30
    assert len(w["acknowledgement_history"])==25
    assert w["acknowledgement_history"][0]["acknowledgement_notes"]=="Review 29."
    assert w["acknowledgement_history"][-1]["acknowledgement_notes"]=="Review 05."
    assert w["latest_acknowledgement"]["acknowledgement_notes"]=="Review 29."

def test_history_snapshots_remain_point_in_time_records():
    j=job();r=repo_for(j)
    r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="Before completion.",acknowledged_by="Leandra")
    first=r.project_lifecycle_audit_acknowledgements(job_number=j.job_number)[0]
    assert first["audit_snapshot"]["completion_status"]=="NOT_CERTIFIED"
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Completion certified.",authorized_by="Leandra")
    assert r.project_lifecycle_audit_acknowledgements(job_number=j.job_number)[0]["audit_snapshot"]["completion_status"]=="NOT_CERTIFIED"
