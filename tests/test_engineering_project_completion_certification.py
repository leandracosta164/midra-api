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
    return SimpleNamespace(job_number="ENG-PCC",project_name="Completion",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections=sections or {},events=[])

def test_completion_certification_records_final_human_action():
    j=job({"project_closure":{"summary":{"items":[{"status":"COMPLETE"}]}},
           "project_archive":{"summary":{"items":[{"status":"ARCHIVED"}]}},
           "closeout":{"summary":{"items":[{"status":"WAIVED"}]}},
           "punch_list":{"summary":{"items":[{"status":"COMPLETE"}]}}})
    r=repo_for(j)
    r.certify_project_completion(job_number=j.job_number,certification_type="PROJECT_COMPLETE",
        completion_date="2026-09-22",certification_notes="Final project obligations reviewed and complete.",
        authorized_by="Leandra")
    c=engineering_workspace(j)["project_completion"]
    assert c["certified"] is True
    assert c["certification"]["status"]=="CERTIFIED"
    assert c["certification"]["certified_by"]=="Leandra"
    assert j.events[-1]["event_type"]=="PROJECT_COMPLETION_CERTIFIED"

def test_completion_fails_closed_with_open_closure_item():
    j=job({"project_closure":{"summary":{"items":[{"status":"OPEN"}]}}});r=repo_for(j)
    try:r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Attempted completion.",authorized_by="Leandra")
    except ValueError as exc: assert "closure items" in str(exc)
    else: raise AssertionError("completion certified with open closure item")

def test_completion_fails_closed_with_unarchived_record():
    j=job({"project_archive":{"summary":{"items":[{"status":"VERIFIED"}]}}});r=repo_for(j)
    try:r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Attempted completion.",authorized_by="Leandra")
    except ValueError as exc: assert "archive records" in str(exc)
    else: raise AssertionError("completion certified with unarchived record")

def test_completion_fails_closed_with_open_closeout_or_punch():
    for section,msg in [("closeout","closeout items"),("punch_list","punch-list items")]:
        j=job({section:{"summary":{"items":[{"status":"OPEN"}]}}});r=repo_for(j)
        try:r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
            certification_notes="Attempted completion.",authorized_by="Leandra")
        except ValueError as exc: assert msg in str(exc)
        else: raise AssertionError("completion certified with unresolved "+section)

def test_completion_cannot_be_certified_twice():
    j=job();r=repo_for(j)
    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Complete.",authorized_by="Leandra")
    try:r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Again.",authorized_by="Leandra")
    except ValueError as exc: assert "already been certified" in str(exc)
    else: raise AssertionError("duplicate completion certification accepted")
