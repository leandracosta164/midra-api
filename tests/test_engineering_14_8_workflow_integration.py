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
    return SimpleNamespace(job_number="ENG-148",project_name="Workflow Integration",
        project_type="SITE",source="TEST",property_address="1 Project Way",
        client_id="CLIENT-1",state="ACTIVE",version=14,sections={},events=[])

def test_revision_lifecycle_uses_real_document_storage_contract():
    j=job(); r=repo_for(j)
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="site-plan.pdf",
        content_type="application/pdf",category="PLAN",description="Site plan",
        deliverable_id=None,storage_path="documents/site-plan.pdf",sha256="abc",size_bytes=100,
        authorized_by="Leandra")
    r.add_document_revision(job_number=j.job_number,document_id="DOC-1",
        filename="site-plan-r2.pdf",content_type="application/pdf",description="Revision 2",
        storage_path="documents/site-plan-r2.pdf",sha256="def",size_bytes=120,authorized_by="Leandra")
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="2",
        status="IN_REVIEW",authorized_by="Leandra")
    doc=j.sections["documents"]["summary"]["items"][0]
    assert doc["revisions"][1]["status"]=="IN_REVIEW"
    assert doc["current_revision"]==2
    assert doc["current_revision_status"]=="IN_REVIEW"

def test_review_lifecycle_uses_real_review_and_comment_contract():
    j=job(); r=repo_for(j)
    r.add_review(job_number=j.job_number,title="Design Review",authorized_by="Leandra")
    rid=j.sections["reviews"]["summary"]["items"][0]["review_id"]
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="1",
        comment_text="Revise note",authorized_by="Leandra")
    cid=j.sections["reviews"]["summary"]["items"][0]["comments"][0]["comment_id"]
    try:
        r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="CLOSED",authorized_by="Leandra")
    except ValueError: pass
    else: raise AssertionError("review closed with unresolved actionable comment")
    r.update_review_comment(job_number=j.job_number,review_id=rid,comment_id=cid,
        status="VERIFIED",authorized_by="Leandra")
    r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="CLOSED",authorized_by="Leandra")
    assert j.sections["reviews"]["summary"]["items"][0]["status"]=="CLOSED"

def test_non_actionable_comment_does_not_block_close():
    j=job(); r=repo_for(j)
    r.add_review(job_number=j.job_number,title="Coordination Review",authorized_by="Leandra")
    rid=j.sections["reviews"]["summary"]["items"][0]["review_id"]
    r.add_review_comment(job_number=j.job_number,review_id=rid,comment_number="INFO-1",
        comment_text="Informational",requires_action=False,authorized_by="Leandra")
    r.update_review_cycle_status(job_number=j.job_number,review_id=rid,status="CLOSED",authorized_by="Leandra")
    assert j.sections["reviews"]["summary"]["items"][0]["status"]=="CLOSED"
