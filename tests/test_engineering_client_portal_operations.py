from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self, job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r

def job():
    return SimpleNamespace(job_number="ENG-145",project_name="Portal Ops",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=14,sections={},events=[])

def test_create_portal_item_flows_into_existing_register():
    j=job(); r=repo_for(j)
    r.add_client_portal_item(job_number=j.job_number,title="Review package",item_type="DOCUMENT",
        status="SHARED",acknowledgement_required=True,client_action_required=True,authorized_by="Leandra")
    w=engineering_workspace(j)
    assert w["client_portal"]["count"]==1
    assert w["client_portal"]["shared_count"]==1
    assert w["client_portal"]["acknowledgement_required_count"]==1
    assert w["client_portal"]["client_action_required_count"]==1
    assert j.events[-1]["event_type"]=="CLIENT_PORTAL_ITEM_RECORDED"

def test_update_portal_acknowledgement_and_client_action():
    j=job(); r=repo_for(j)
    r.add_client_portal_item(job_number=j.job_number,title="Client decision",status="AVAILABLE",
        acknowledgement_required=True,client_action_required=True,authorized_by="Leandra")
    pid=j.sections["client_portal"]["summary"]["items"][0]["portal_item_id"]
    r.update_client_portal_item(job_number=j.job_number,portal_item_id=pid,
        acknowledgement_status="ACKNOWLEDGED",client_action_status="COMPLETED",authorized_by="Leandra")
    w=engineering_workspace(j)
    assert w["client_portal"]["acknowledgement_required_count"]==0
    assert w["client_portal"]["client_action_required_count"]==0
    assert j.events[-1]["event_type"]=="CLIENT_PORTAL_ITEM_UPDATED"

def test_portal_does_not_infer_client_completion():
    j=job(); r=repo_for(j)
    r.add_client_portal_item(job_number=j.job_number,title="Notice",status="PUBLISHED",
        acknowledgement_required=True,authorized_by="Leandra")
    item=j.sections["client_portal"]["summary"]["items"][0]
    assert item["acknowledgement_status"]=="PENDING"
