from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n)); return r
def job():
    return SimpleNamespace(job_number="ENG-152",project_name="Returned Submission",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=15,sections={},events=[])
def submitted(r,j):
    r.add_deliverable(job_number=j.job_number,title="Site Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][0]["deliverable_id"]
    r.change_deliverable_status(job_number=j.job_number,deliverable_id=did,status="READY_FOR_REVIEW",authorized_by="Leandra")
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="site-plan.pdf",
        content_type="application/pdf",category="PLAN",description="Site plan",deliverable_id=did,
        storage_path="documents/site-plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",authorized_by="Leandra")
    r.add_submission_package(job_number=j.job_number,title="Agency Package",recipient="Agency",
        deliverable_ids=[did],document_ids=["DOC-1"],authorized_by="Leandra")
    pid=j.sections["submission_packages"]["summary"]["items"][0]["package_id"]
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.advance_submission_package(job_number=j.job_number,package_id=pid,status="SUBMITTED",authorized_by="Leandra")
    return pid
def test_return_work_requires_confirmed_return_outcome():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    try: r.activate_submission_return_work(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "confirmed returned or rejected" in str(exc)
    else: raise AssertionError("return work activated without returned outcome")
def test_returned_submission_activates_real_action_item():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    r.record_submission_outcome(job_number=j.job_number,package_id=pid,outcome="RETURNED",
        reference="AGENCY-17",notes="Address comments",authorized_by="Leandra")
    r.activate_submission_return_work(job_number=j.job_number,package_id=pid,owner="Project Engineer",
        due_at="2026-10-01",priority="HIGH",authorized_by="Leandra")
    item=j.sections["action_items"]["summary"]["items"][0]
    assert item["status"]=="OPEN" and item["related_package_id"]==pid
    assert item["action_type"]=="SUBMISSION_RETURN"
    assert item["activation_source"]=="SUBMISSION_RETURN"
    assert j.events[-1]["event_type"]=="SUBMISSION_RETURN_WORK_ACTIVATED"
def test_duplicate_active_return_work_is_blocked():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    r.record_submission_outcome(job_number=j.job_number,package_id=pid,outcome="REJECTED",authorized_by="Leandra")
    r.activate_submission_return_work(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    try: r.activate_submission_return_work(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "already exists" in str(exc)
    else: raise AssertionError("duplicate active return work created")
