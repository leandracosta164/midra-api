from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n)); return r
def job():
    return SimpleNamespace(job_number="ENG-156",project_name="Lifecycle Summary",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=15,sections={},events=[])
def add_ready_package(r,j,title,doc_id):
    r.add_deliverable(job_number=j.job_number,title=title+" Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][-1]["deliverable_id"]
    r.change_deliverable_status(job_number=j.job_number,deliverable_id=did,status="READY_FOR_REVIEW",authorized_by="Leandra")
    r.add_document(job_number=j.job_number,document_id=doc_id,filename=doc_id+".pdf",
        content_type="application/pdf",category="PLAN",description=title,deliverable_id=did,
        storage_path="documents/"+doc_id+".pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.update_document_revision_status(job_number=j.job_number,document_id=doc_id,revision_id="1",
        status="READY",authorized_by="Leandra")
    r.add_submission_package(job_number=j.job_number,title=title,recipient="Agency",
        deliverable_ids=[did],document_ids=[doc_id],authorized_by="Leandra")
    pid=j.sections["submission_packages"]["summary"]["items"][-1]["package_id"]
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.advance_submission_package(job_number=j.job_number,package_id=pid,status="SUBMITTED",authorized_by="Leandra")
    return pid
def test_summary_counts_real_submission_states():
    j=job(); r=repo_for(j)
    p1=add_ready_package(r,j,"Accepted Package","DOC-A")
    r.record_submission_outcome(job_number=j.job_number,package_id=p1,outcome="ACCEPTED",
        reference="A-1",authorized_by="Leandra")
    r.close_accepted_submission(job_number=j.job_number,package_id=p1,authorized_by="Leandra")
    p2=add_ready_package(r,j,"Returned Package","DOC-B")
    r.record_submission_outcome(job_number=j.job_number,package_id=p2,outcome="RETURNED",
        reference="R-1",authorized_by="Leandra")
    r.activate_submission_return_work(job_number=j.job_number,package_id=p2,authorized_by="Leandra")
    s=r.get_submission_lifecycle_summary(job_number=j.job_number)
    assert s["package_count"]==2
    assert s["status_counts"]["CLOSED"]==1 and s["status_counts"]["RETURNED"]==1
    assert s["attention_packages"][0]["package_id"]==p2
    assert s["attention_packages"][0]["open_return_work"]==1
def test_summary_does_not_invent_attention_for_closed_package():
    j=job(); r=repo_for(j)
    p=add_ready_package(r,j,"Accepted Package","DOC-C")
    r.record_submission_outcome(job_number=j.job_number,package_id=p,outcome="ACCEPTED",authorized_by="Leandra")
    r.close_accepted_submission(job_number=j.job_number,package_id=p,authorized_by="Leandra")
    s=r.get_submission_lifecycle_summary(job_number=j.job_number)
    assert s["attention_packages"]==[]
    assert s["status_counts"]=={"CLOSED":1}
