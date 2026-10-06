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
    return SimpleNamespace(job_number="ENG-149",project_name="Submission Readiness",
        project_type="SITE",source="TEST",property_address="1 Project Way",client_id="CLIENT-1",
        state="ACTIVE",version=14,sections={},events=[])

def build_package(r,j):
    r.add_deliverable(job_number=j.job_number,title="Site Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][0]["deliverable_id"]
    r.change_deliverable_status(job_number=j.job_number,deliverable_id=did,status="READY_FOR_REVIEW",
        authorized_by="Leandra")
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="site-plan.pdf",
        content_type="application/pdf",category="PLAN",description="Site plan",deliverable_id=did,
        storage_path="documents/site-plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.add_submission_package(job_number=j.job_number,title="Agency Package",recipient="Agency",
        deliverable_ids=[did],document_ids=["DOC-1"],authorized_by="Leandra")
    return did,j.sections["submission_packages"]["summary"]["items"][0]["package_id"]

def test_readiness_blocks_unclassified_current_revision():
    j=job(); r=repo_for(j); _,pid=build_package(r,j)
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    readiness=j.sections["submission_packages"]["summary"]["items"][0]["readiness"]
    assert readiness["status"]=="BLOCKED"
    assert any(x["type"]=="DOCUMENT_REVISION_NOT_READY" for x in readiness["blockers"])

def test_ready_revision_and_resolved_review_produce_operational_ready():
    j=job(); r=repo_for(j); _,pid=build_package(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",authorized_by="Leandra")
    r.add_review(job_number=j.job_number,title="Internal Review",source_document_id="DOC-1",authorized_by="Leandra")
    rid=j.sections["reviews"]["summary"]["items"][0]["review_id"]
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="1",
        comment_text="Coordinate note",authorized_by="Leandra")
    cid=j.sections["reviews"]["summary"]["items"][0]["comments"][0]["comment_id"]
    r.update_review_comment(job_number=j.job_number,review_id=rid,comment_id=cid,status="VERIFIED",
        authorized_by="Leandra")
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    readiness=j.sections["submission_packages"]["summary"]["items"][0]["readiness"]
    assert readiness["status"]=="READY"
    assert readiness["blockers"]==[]
    assert j.events[-1]["event_type"]=="SUBMISSION_READINESS_ASSESSED"

def test_unresolved_actionable_review_comment_blocks_readiness():
    j=job(); r=repo_for(j); _,pid=build_package(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",authorized_by="Leandra")
    r.add_review(job_number=j.job_number,title="Internal Review",source_document_id="DOC-1",authorized_by="Leandra")
    rid=j.sections["reviews"]["summary"]["items"][0]["review_id"]
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="1",
        comment_text="Revise note",authorized_by="Leandra")
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    blockers=j.sections["submission_packages"]["summary"]["items"][0]["readiness"]["blockers"]
    assert any(x["type"]=="UNRESOLVED_REVIEW_COMMENTS" for x in blockers)
