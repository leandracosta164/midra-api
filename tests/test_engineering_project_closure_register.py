from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"project_closure":{"reference_id":"CLOSURE-1","summary":{"items":items}}},
        job_number="ENG-C1",project_name="Closure",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=19,events=[])

def test_project_closure_projection_counts():
    items=[{"closure_id":"C1","status":"OPEN"},{"closure_id":"C2","status":"IN_PROGRESS"},
           {"closure_id":"C3","status":"READY_FOR_REVIEW"},{"closure_id":"C4","status":"COMPLETE"},
           {"closure_id":"C5","status":"WAIVED"}]
    c=engineering_workspace(job(items))["project_closure"]
    assert c["count"]==5 and c["open_count"]==2 and c["review_count"]==1
    assert c["complete_count"]==1 and c["waived_count"]==1

def test_empty_project_closure_register_is_explicit():
    assert engineering_workspace(job([]))["project_closure"]=={
        "items":[],"count":0,"open_count":0,"review_count":0,"complete_count":0,"waived_count":0}
