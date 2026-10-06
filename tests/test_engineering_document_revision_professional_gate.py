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
    return SimpleNamespace(job_number="ENG-161",project_name="Lifecycle UI",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=16,sections={},events=[])

def create_document(r,j):
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="plan.pdf",
        content_type="application/pdf",category="PLAN",description=None,deliverable_id=None,
        storage_path="documents/plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")

def test_issued_revision_requires_explicit_professional_approval():
    j=job(); r=repo_for(j); create_document(r,j)
    try:
        r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
            status="ISSUED",professional_approval=False,authorized_by="Leandra")
    except ValueError as exc:
        assert "explicit professional approval" in str(exc)
    else:
        raise AssertionError("issued revision was recorded without explicit professional approval")

def test_issued_revision_records_explicit_professional_approval():
    j=job(); r=repo_for(j); create_document(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="ISSUED",professional_approval=True,authorized_by="Leandra")
    rev=j.sections["documents"]["summary"]["items"][0]["revisions"][0]
    assert rev["status"]=="ISSUED"
    assert j.events[-1]["professional_action_approved"] is True

def test_non_issued_revision_status_remains_open_without_professional_approval():
    j=job(); r=repo_for(j); create_document(r,j)
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",professional_approval=False,authorized_by="Leandra")
    assert j.sections["documents"]["summary"]["items"][0]["revisions"][0]["status"]=="READY"
