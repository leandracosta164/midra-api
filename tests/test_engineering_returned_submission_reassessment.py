from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n)); return r
def job():
    return SimpleNamespace(job_number="ENG-153",project_name="Return Reassessment",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=15,sections={},events=[])
def returned(r,j):
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
    r.record_submission_outcome(job_number=j.job_number,package_id=pid,outcome="RETURNED",
        notes="Agency comments",authorized_by="Leandra")
    r.activate_submission_return_work(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    return pid
def test_reassessment_blocked_while_return_work_open():
    j=job(); r=repo_for(j); pid=returned(r,j)
    try: r.reassess_returned_submission(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "return work must be completed before reassessment" in str(exc)
    else: raise AssertionError("returned package reassessed while return work remained open")
def test_completed_return_work_allows_reassessment():
    j=job(); r=repo_for(j); pid=returned(r,j)
    item=j.sections["action_items"]["summary"]["items"][0]
    r.update_action_item(job_number=j.job_number,action_id=item["action_id"],status="DONE",
        completion_note="Return work completed",authorized_by="Leandra")
    r.reassess_returned_submission(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    package=j.sections["submission_packages"]["summary"]["items"][0]
    assert package["readiness"]["status"]=="READY"
    assert j.events[-1]["event_type"]=="RETURNED_SUBMISSION_REASSESSED"
def test_return_reassessment_requires_returned_package():
    j=job(); r=repo_for(j)
    r.add_deliverable(job_number=j.job_number,title="Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][0]["deliverable_id"]
    r.add_submission_package(job_number=j.job_number,title="Draft",recipient="Agency",
        deliverable_ids=[did],authorized_by="Leandra")
    pid=j.sections["submission_packages"]["summary"]["items"][0]["package_id"]
    try: r.reassess_returned_submission(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    except ValueError as exc: assert "returned submission package" in str(exc)
    else: raise AssertionError("non-returned package entered return reassessment")
