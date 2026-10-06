from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"punch_list":{"reference_id":"PUNCH-1","summary":{"items":items}}},
        job_number="ENG-P1",project_name="Punch",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=18,events=[])

def test_punch_list_projection_counts():
    items=[{"punch_id":"P1","status":"OPEN","priority":"URGENT"},
           {"punch_id":"P2","status":"IN_PROGRESS","priority":"NORMAL"},
           {"punch_id":"P3","status":"READY_FOR_VERIFICATION","priority":"HIGH"},
           {"punch_id":"P4","status":"CLOSED","priority":"URGENT"}]
    p=engineering_workspace(job(items))["punch_list"]
    assert p["count"]==4 and p["open_count"]==2 and p["verification_count"]==1
    assert p["closed_count"]==1 and p["urgent_count"]==1

def test_empty_punch_list_is_explicit():
    assert engineering_workspace(job([]))["punch_list"]=={
        "items":[],"count":0,"open_count":0,"verification_count":0,"closed_count":0,"urgent_count":0}
