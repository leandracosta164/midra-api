from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n)); return r
def job():
    return SimpleNamespace(job_number="ENG-155",project_name="Accepted Closure",project_type="SITE",
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
def test_closure_blocked_without_confirmed_acceptance():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    try: r.close_accepted_submission(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "confirmed accepted outcome" in str(exc)
    else: raise AssertionError("submission closed without confirmed acceptance")
def test_confirmed_acceptance_can_close_submission():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    r.record_submission_outcome(job_number=j.job_number,package_id=pid,outcome="ACCEPTED",
        reference="AGENCY-ACCEPT-22",notes="Accepted by agency",authorized_by="Leandra")
    r.close_accepted_submission(job_number=j.job_number,package_id=pid,
        closure_note="External acceptance recorded; close submission cycle",authorized_by="Leandra")
    package=j.sections["submission_packages"]["summary"]["items"][0]
    assert package["status"]=="CLOSED"
    assert package["outcome"]["status"]=="ACCEPTED"
    assert package["closure"]["accepted_reference"]=="AGENCY-ACCEPT-22"
    assert j.events[-1]["event_type"]=="ACCEPTED_SUBMISSION_CLOSED"
def test_returned_submission_cannot_use_acceptance_closure():
    j=job(); r=repo_for(j); pid=submitted(r,j)
    r.record_submission_outcome(job_number=j.job_number,package_id=pid,outcome="RETURNED",
        reference="AGENCY-RETURN-22",authorized_by="Leandra")
    try: r.close_accepted_submission(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "confirmed accepted outcome" in str(exc)
    else: raise AssertionError("returned submission closed through accepted closure path")
