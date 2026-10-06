from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository

class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r

def job():
    return SimpleNamespace(job_number="ENG-150",project_name="Submission Gate",
        project_type="SITE",source="TEST",property_address="1 Project Way",client_id="CLIENT-1",
        state="ACTIVE",version=15,sections={},events=[])

def build(r,j):
    r.add_deliverable(job_number=j.job_number,title="Site Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][0]["deliverable_id"]
    r.change_deliverable_status(job_number=j.job_number,deliverable_id=did,status="READY_FOR_REVIEW",authorized_by="Leandra")
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="site-plan.pdf",
        content_type="application/pdf",category="PLAN",description="Site plan",deliverable_id=did,
        storage_path="documents/site-plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.add_submission_package(job_number=j.job_number,title="Agency Package",recipient="Agency",
        deliverable_ids=[did],document_ids=["DOC-1"],authorized_by="Leandra")
    return j.sections["submission_packages"]["summary"]["items"][0]["package_id"]

def test_package_cannot_advance_to_ready_without_readiness():
    j=job(); r=repo_for(j); pid=build(r,j)
    try:
        r.advance_submission_package(job_number=j.job_number,package_id=pid,status="READY",authorized_by="Leandra")
    except ValueError as exc:
        assert "not operationally ready" in str(exc)
    else:
        raise AssertionError("package advanced without readiness")

def test_ready_assessment_unlocks_ready_status():
    j=job(); r=repo_for(j); pid=build(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",authorized_by="Leandra")
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.advance_submission_package(job_number=j.job_number,package_id=pid,status="READY",authorized_by="Leandra")
    package=j.sections["submission_packages"]["summary"]["items"][0]
    assert package["status"]=="READY"
    assert package["readiness"]["status"]=="READY"
    assert j.events[-1]["event_type"]=="SUBMISSION_PACKAGE_STATUS_ADVANCED"

def test_blocked_reassessment_prevents_submission():
    j=job(); r=repo_for(j); pid=build(r,j)
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    try:
        r.advance_submission_package(job_number=j.job_number,package_id=pid,status="SUBMITTED",authorized_by="Leandra")
    except ValueError:
        pass
    else:
        raise AssertionError("blocked package advanced to submitted")
