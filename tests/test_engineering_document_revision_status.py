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
    return SimpleNamespace(job_number="ENG-146",project_name="Revision Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=14,sections={},events=[])

def create_document_and_revision(r,j):
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="site-plan.pdf",
        content_type="application/pdf",category="PLAN",description="Site plan",deliverable_id=None,
        storage_path="documents/site-plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.add_document_revision(job_number=j.job_number,document_id="DOC-1",filename="site-plan-r2.pdf",
        content_type="application/pdf",description="Revision 2",storage_path="documents/site-plan-r2.pdf",
        sha256="def",size_bytes=120,authorized_by="Leandra")

def test_revision_status_progression_is_recorded():
    j=job(); r=repo_for(j); create_document_and_revision(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="2",
        status="IN_REVIEW",notes="Internal review",authorized_by="Leandra")
    doc=j.sections["documents"]["summary"]["items"][0]
    assert doc["revisions"][1]["status"]=="IN_REVIEW"
    assert doc["current_revision_status"]=="IN_REVIEW"
    assert j.events[-1]["event_type"]=="DOCUMENT_REVISION_STATUS_CHANGED"

def test_revision_can_be_marked_ready_without_implying_issue():
    j=job(); r=repo_for(j); create_document_and_revision(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="2",
        status="READY",authorized_by="Leandra")
    assert j.sections["documents"]["summary"]["items"][0]["revisions"][1]["status"]=="READY"
    assert j.events[-1]["to_status"]=="READY"

def test_invalid_revision_status_fails_closed():
    j=job(); r=repo_for(j); create_document_and_revision(r,j)
    try:
        r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="2",
            status="APPROVED_BY_ENGINEER",authorized_by="Leandra")
    except ValueError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("unsupported revision status was accepted")
