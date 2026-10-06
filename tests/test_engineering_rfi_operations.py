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
    return SimpleNamespace(job_number="ENG-RFI2",project_name="RFI Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=17,sections={},events=[])

def test_create_answer_and_close_rfi():
    j=job();r=repo_for(j)
    r.add_rfi(job_number=j.job_number,subject="Clarify beam elevation",
        question="Confirm required elevation.",priority="URGENT",authorized_by="Leandra")
    rid=j.sections["rfis"]["summary"]["items"][0]["rfi_id"]
    assert engineering_workspace(j)["rfis"]["urgent_count"]==1
    r.update_rfi(job_number=j.job_number,rfi_id=rid,status="ANSWERED",
        response="Use elevation shown on revised detail.",responded_by="Engineer",authorized_by="Leandra")
    assert engineering_workspace(j)["rfis"]["answered_count"]==1
    r.update_rfi(job_number=j.job_number,rfi_id=rid,status="CLOSED",
        response="Use elevation shown on revised detail.",authorized_by="Leandra")
    assert engineering_workspace(j)["rfis"]["closed_count"]==1
    assert j.events[-1]["event_type"]=="RFI_STATUS_CHANGED"

def test_answered_rfi_requires_response():
    j=job();r=repo_for(j)
    r.add_rfi(job_number=j.job_number,subject="X",question="Y",authorized_by="Leandra")
    rid=j.sections["rfis"]["summary"]["items"][0]["rfi_id"]
    try:r.update_rfi(job_number=j.job_number,rfi_id=rid,status="ANSWERED",authorized_by="Leandra")
    except ValueError as exc: assert "response" in str(exc)
    else: raise AssertionError("answered RFI accepted without response")

def test_invalid_rfi_priority_fails_closed():
    j=job();r=repo_for(j)
    try:r.add_rfi(job_number=j.job_number,subject="X",question="Y",priority="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "priority" in str(exc)
    else: raise AssertionError("invalid RFI priority accepted")
