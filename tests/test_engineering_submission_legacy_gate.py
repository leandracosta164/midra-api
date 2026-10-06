from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n)); return r
def job():
    return SimpleNamespace(job_number="ENG-157",project_name="Legacy Gate",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=15,sections={},events=[])
def package(r,j):
    r.add_deliverable(job_number=j.job_number,title="Plan",deliverable_type="PLAN",authorized_by="Leandra")
    did=j.sections["deliverables"]["summary"]["items"][0]["deliverable_id"]
    r.change_deliverable_status(job_number=j.job_number,deliverable_id=did,status="READY_FOR_REVIEW",authorized_by="Leandra")
    r.add_document(job_number=j.job_number,document_id="DOC-1",filename="plan.pdf",
        content_type="application/pdf",category="PLAN",description="Plan",deliverable_id=did,
        storage_path="documents/plan.pdf",sha256="abc",size_bytes=100,authorized_by="Leandra")
    r.update_document_revision_status(job_number=j.job_number,document_id="DOC-1",revision_id="1",
        status="READY",authorized_by="Leandra")
    r.add_submission_package(job_number=j.job_number,title="Agency Package",recipient="Agency",
        deliverable_ids=[did],document_ids=["DOC-1"],authorized_by="Leandra")
    return j.sections["submission_packages"]["summary"]["items"][0]["package_id"]
def test_legacy_ready_status_cannot_bypass_readiness_gate():
    j=job(); r=repo_for(j); pid=package(r,j)
    try:
        r.change_submission_package_status(job_number=j.job_number,package_id=pid,status="READY",
            professional_approval=False,authorized_by="Leandra")
    except ValueError as exc: assert "not operationally ready" in str(exc)
    else: raise AssertionError("legacy route bypassed readiness gate")
def test_legacy_submitted_status_uses_controlled_advancement_and_preserves_metadata():
    j=job(); r=repo_for(j); pid=package(r,j)
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.change_submission_package_status(job_number=j.job_number,package_id=pid,status="SUBMITTED",
        submitted_at="2026-09-20",reference="TR-157",note="Portal submission",
        professional_approval=True,authorized_by="Leandra")
    pkg=j.sections["submission_packages"]["summary"]["items"][0]
    assert pkg["status"]=="SUBMITTED" and pkg["submitted_at"]=="2026-09-20"
    assert pkg["reference"]=="TR-157" and pkg["status_note"]=="Portal submission"
    assert any(e["event_type"]=="SUBMISSION_PACKAGE_STATUS_ADVANCED" and e["to_status"]=="SUBMITTED" for e in j.events)
def test_legacy_returned_status_records_real_external_outcome():
    j=job(); r=repo_for(j); pid=package(r,j)
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.advance_submission_package(job_number=j.job_number,package_id=pid,status="SUBMITTED",authorized_by="Leandra")
    r.change_submission_package_status(job_number=j.job_number,package_id=pid,status="RETURNED",
        reference="AGENCY-R-157",note="Comments issued",professional_approval=False,authorized_by="Leandra")
    pkg=j.sections["submission_packages"]["summary"]["items"][0]
    assert pkg["status"]=="RETURNED"
    assert pkg["outcome"]["status"]=="RETURNED" and pkg["outcome"]["reference"]=="AGENCY-R-157"
    assert j.events[-1]["event_type"]=="SUBMISSION_OUTCOME_RECORDED"
def test_legacy_accepted_status_requires_explicit_approval_and_records_outcome():
    j=job(); r=repo_for(j); pid=package(r,j)
    r.assess_submission_package_readiness(job_number=j.job_number,package_id=pid,authorized_by="Leandra")
    r.advance_submission_package(job_number=j.job_number,package_id=pid,status="SUBMITTED",authorized_by="Leandra")
    try:
        r.change_submission_package_status(job_number=j.job_number,package_id=pid,status="ACCEPTED",
            reference="A-157",professional_approval=False,authorized_by="Leandra")
    except ValueError as exc: assert "explicit professional approval" in str(exc)
    else: raise AssertionError("legacy accepted status bypassed explicit approval")
    r.change_submission_package_status(job_number=j.job_number,package_id=pid,status="ACCEPTED",
        reference="A-157",professional_approval=True,authorized_by="Leandra")
    pkg=j.sections["submission_packages"]["summary"]["items"][0]
    assert pkg["outcome"]["status"]=="ACCEPTED"
    assert j.events[-1]["event_type"]=="SUBMISSION_OUTCOME_RECORDED"
