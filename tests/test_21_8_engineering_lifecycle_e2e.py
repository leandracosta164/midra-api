from types import SimpleNamespace
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_workspace_dashboard import engineering_workspace

class FakeDB:
    def commit(self): pass
    def refresh(self,job): pass

def repo_for(job):
    r=object.__new__(SQLAlchemyEngineeringJobRepository); r.db=FakeDB()
    r.get=lambda n: job if n==job.job_number else (_ for _ in ()).throw(KeyError(n))
    return r

def job():
    return SimpleNamespace(job_number="ENG-E2E",project_name="Lifecycle E2E",project_type="SITE",
        source="TEST",property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",
        version=20,sections={},events=[])

def audit_status(a):
    c=a.get("completion_certification")
    if c:return str(c.get("status","")).upper() or "CERTIFIED"
    if a.get("reopen_history"):return "REOPENED"
    return "NOT_CERTIFIED"

def cert_count(a):
    return len(a.get("certification_history") or [])+(1 if a.get("completion_certification") else 0)

def open_count(a):
    return sum(1 for x in (a.get("post_completion_work") or [])
               if str(x.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"})

def test_full_engineering_lifecycle_end_to_end():
    j=job();r=repo_for(j)
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert audit_status(a)=="NOT_CERTIFIED" and cert_count(a)==0 and open_count(a)==0

    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Initial completion certified.",authorized_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert audit_status(a)=="CERTIFIED" and cert_count(a)==1

    r.reopen_completed_project(job_number=j.job_number,
        reason="Additional field condition requires review.",authorized_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert audit_status(a)=="REOPENED" and len(a.get("reopen_history") or [])==1

    r.add_post_completion_work(job_number=j.job_number,title="Field condition review",
        work_type="CORRECTION",description="Review newly documented field condition.",
        authorized_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert open_count(a)==1
    item=(a.get("post_completion_work") or [])[0]
    assert item.get("item_id")

    r.update_post_completion_work(job_number=j.job_number,item_id=item["item_id"],
        status="RESOLVED",resolution_notes="Field condition reviewed and disposition recorded.",
        authorized_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert open_count(a)==0

    r.certify_project_completion(job_number=j.job_number,completion_date="2026-09-22",
        certification_notes="Completion re-certified after field-condition review.",
        authorized_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert audit_status(a)=="CERTIFIED" and cert_count(a)==2 and len(a.get("reopen_history") or [])==1

    before=(audit_status(a),cert_count(a),len(a.get("reopen_history") or []),open_count(a))
    r.acknowledge_project_lifecycle_audit(job_number=j.job_number,
        acknowledgement_notes="Final lifecycle audit reviewed.",acknowledged_by="Leandra")
    a=r.project_lifecycle_audit(job_number=j.job_number)
    assert (audit_status(a),cert_count(a),len(a.get("reopen_history") or []),open_count(a))==before
    assert len(a["acknowledgements"])==1
    assert a["acknowledgements"][0]["audit_snapshot"]=={
        "completion_status":"CERTIFIED","certification_count":2,
        "reopen_count":1,"post_completion_open_count":0}

    w=engineering_workspace(j)["lifecycle_audit"]
    assert w["completion_status"]=="CERTIFIED"
    assert w["certification_count"]==2
    assert w["reopen_count"]==1
    assert w["post_completion_open_count"]==0
    assert w["acknowledgement_count"]==1
    assert len(w["acknowledgement_history"])==1

    event_types=[e.get("event_type") for e in j.events]
    for expected in ["PROJECT_COMPLETION_CERTIFIED","PROJECT_REOPENED_AFTER_COMPLETION",
        "POST_COMPLETION_WORK_OPENED","POST_COMPLETION_WORK_STATUS_CHANGED",
        "PROJECT_LIFECYCLE_AUDIT_ACKNOWLEDGED"]:
        assert expected in event_types
