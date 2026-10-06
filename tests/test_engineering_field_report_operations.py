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
    return SimpleNamespace(job_number="ENG-F2",project_name="Field Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=17,sections={},events=[])

def test_create_and_close_field_report():
    j=job();r=repo_for(j)
    r.add_field_report(job_number=j.job_number,title="Site observation",report_type="SITE_VISIT",
        observations="Observed installed work.",follow_up_required=True,authorized_by="Leandra")
    rid=j.sections["field_reports"]["summary"]["items"][0]["report_id"]
    assert engineering_workspace(j)["field_reports"]["follow_up_count"]==1
    r.update_field_report(job_number=j.job_number,report_id=rid,status="CLOSED",
        follow_up_required=False,authorized_by="Leandra")
    assert engineering_workspace(j)["field_reports"]["closed_count"]==1
    assert j.events[-1]["event_type"]=="FIELD_REPORT_STATUS_CHANGED"

def test_invalid_field_report_status_fails_closed():
    j=job();r=repo_for(j)
    r.add_field_report(job_number=j.job_number,title="X",observations="Y",authorized_by="Leandra")
    rid=j.sections["field_reports"]["summary"]["items"][0]["report_id"]
    try:r.update_field_report(job_number=j.job_number,report_id=rid,status="MAGIC",authorized_by="Leandra")
    except ValueError as exc: assert "status" in str(exc)
    else: raise AssertionError("invalid field report status accepted")
