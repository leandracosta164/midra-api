from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"milestones":{"reference_id":"MILE-1","summary":{"items":items}}},
        job_number="ENG-M1",project_name="Milestones",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=16,events=[])

def test_milestone_register_projects_status_counts():
    items=[{"milestone_id":"M1","status":"OPEN"},{"milestone_id":"M2","status":"BLOCKED"},
           {"milestone_id":"M3","status":"COMPLETE"}]
    m=engineering_workspace(job(items))["milestones"]
    assert m["count"]==3 and m["open_count"]==2 and m["blocked_count"]==1 and m["complete_count"]==1

def test_empty_milestone_register_is_explicit():
    assert engineering_workspace(job([]))["milestones"]=={
        "items":[],"count":0,"open_count":0,"blocked_count":0,"complete_count":0}
