from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"project_archive":{"reference_id":"ARCHIVE-1","summary":{"items":items}}},
        job_number="ENG-A1",project_name="Archive",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=19,events=[])

def test_archive_projection_counts():
    items=[{"archive_id":"A1","status":"PENDING"},{"archive_id":"A2","status":"READY_FOR_VERIFICATION"},
           {"archive_id":"A3","status":"VERIFIED"},{"archive_id":"A4","status":"ARCHIVED"}]
    a=engineering_workspace(job(items))["project_archive"]
    assert a["count"]==4 and a["pending_count"]==1 and a["verification_count"]==1
    assert a["verified_count"]==1 and a["archived_count"]==1

def test_empty_archive_register_is_explicit():
    assert engineering_workspace(job([]))["project_archive"]=={
        "items":[],"count":0,"pending_count":0,"verification_count":0,"verified_count":0,"archived_count":0}
