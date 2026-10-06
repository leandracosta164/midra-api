from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"warranty_issues":{"reference_id":"WARRANTY-1","summary":{"items":items}}},
        job_number="ENG-W1",project_name="Warranty",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=19,events=[])

def test_warranty_projection_counts():
    items=[{"issue_id":"W1","status":"OPEN","priority":"URGENT"},
           {"issue_id":"W2","status":"IN_PROGRESS","priority":"NORMAL"},
           {"issue_id":"W3","status":"READY_FOR_VERIFICATION","priority":"HIGH"},
           {"issue_id":"W4","status":"RESOLVED","priority":"URGENT"}]
    w=engineering_workspace(job(items))["warranty_issues"]
    assert w["count"]==4 and w["open_count"]==2 and w["verification_count"]==1
    assert w["resolved_count"]==1 and w["urgent_count"]==1

def test_empty_warranty_register_is_explicit():
    assert engineering_workspace(job([]))["warranty_issues"]=={
        "items":[],"count":0,"open_count":0,"verification_count":0,"resolved_count":0,"urgent_count":0}
