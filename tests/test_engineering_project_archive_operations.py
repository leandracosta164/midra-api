from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self,job): pass
def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository);r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r
def job():
    return SimpleNamespace(job_number="ENG-A2",project_name="Archive Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=19,sections={},events=[])

def test_create_verify_and_archive_record():
    j=job();r=repo_for(j)
    r.add_archive_record(job_number=j.job_number,title="Issued record drawings",
        record_type="DRAWING",retention_until="2036-12-31",authorized_by="Leandra")
    aid=j.sections["project_archive"]["summary"]["items"][0]["archive_id"]
    assert engineering_workspace(j)["project_archive"]["pending_count"]==1
    r.update_archive_record(job_number=j.job_number,archive_id=aid,status="VERIFIED",
        verification_notes="Record set checked for completeness.",authorized_by="Leandra")
    assert engineering_workspace(j)["project_archive"]["verified_count"]==1
    r.update_archive_record(job_number=j.job_number,archive_id=aid,status="ARCHIVED",
        verification_notes="Transferred to final project archive.",storage_reference="ARCHIVE/ENG-A2/RECORD-DRAWINGS",
        authorized_by="Leandra")
    assert engineering_workspace(j)["project_archive"]["archived_count"]==1

def test_archive_requires_storage_reference():
    j=job();r=repo_for(j)
    r.add_archive_record(job_number=j.job_number,title="Final report",record_type="REPORT",authorized_by="Leandra")
    aid=j.sections["project_archive"]["summary"]["items"][0]["archive_id"]
    try:r.update_archive_record(job_number=j.job_number,archive_id=aid,status="ARCHIVED",
        verification_notes="Verified.",authorized_by="Leandra")
    except ValueError as exc: assert "storage reference" in str(exc)
    else: raise AssertionError("record archived without storage reference")

def test_final_archive_status_requires_verification_notes():
    j=job();r=repo_for(j)
    r.add_archive_record(job_number=j.job_number,title="Permit",record_type="PERMIT",authorized_by="Leandra")
    aid=j.sections["project_archive"]["summary"]["items"][0]["archive_id"]
    try:r.update_archive_record(job_number=j.job_number,archive_id=aid,status="VERIFIED",authorized_by="Leandra")
    except ValueError as exc: assert "verification notes" in str(exc)
    else: raise AssertionError("record verified without verification notes")
