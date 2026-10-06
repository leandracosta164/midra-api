from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository)
    r.db=FakeDB()
    r.get=lambda job_number: job if job_number==job.job_number else (_ for _ in ()).throw(KeyError(job_number))
    return r

def make_job():
    return SimpleNamespace(job_number="ENG-143",project_name="Correspondence Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=14,sections={},events=[])

def test_record_correspondence_and_workspace_projection():
    job=make_job(); r=repo_for(job)
    r.add_correspondence(job_number=job.job_number,direction="INBOUND",subject="Agency comments",
        channel="EMAIL",response_required=True,response_due_at="2026-10-01",authorized_by="Leandra")
    item=job.sections["correspondence"]["summary"]["items"][0]
    assert item["response_status"]=="PENDING"
    w=engineering_workspace(job)
    assert w["correspondence"]["count"]==1
    assert w["correspondence"]["inbound_count"]==1
    assert w["correspondence"]["response_required_count"]==1

def test_response_status_closes_pending_correspondence():
    job=make_job(); r=repo_for(job)
    r.add_correspondence(job_number=job.job_number,direction="OUTBOUND",subject="Response",
        response_required=True,authorized_by="Leandra")
    cid=job.sections["correspondence"]["summary"]["items"][0]["correspondence_id"]
    r.update_correspondence_response(job_number=job.job_number,correspondence_id=cid,
        response_status="RESPONDED",response_note="Sent",authorized_by="Leandra")
    w=engineering_workspace(job)
    assert w["correspondence"]["outbound_count"]==1
    assert w["correspondence"]["response_required_count"]==0

def test_invalid_correspondence_values_fail_closed():
    job=make_job(); r=repo_for(job)
    try:
        r.add_correspondence(job_number=job.job_number,direction="SIDEWAYS",subject="Bad",authorized_by="Leandra")
    except ValueError as exc:
        assert "direction" in str(exc)
    else:
        raise AssertionError("invalid direction was accepted")
