from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"closeout":{"reference_id":"CLOSEOUT-1","summary":{"items":items}}},
        job_number="ENG-C1",project_name="Closeout",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=18,events=[])

def test_closeout_projection_counts():
    items=[{"closeout_id":"C1","status":"OPEN"},{"closeout_id":"C2","status":"IN_PROGRESS"},
           {"closeout_id":"C3","status":"READY_FOR_REVIEW"},{"closeout_id":"C4","status":"ACCEPTED"},
           {"closeout_id":"C5","status":"WAIVED"}]
    c=engineering_workspace(job(items))["closeout"]
    assert c["count"]==5 and c["open_count"]==2 and c["review_count"]==1
    assert c["accepted_count"]==1 and c["waived_count"]==1

def test_empty_closeout_register_is_explicit():
    assert engineering_workspace(job([]))["closeout"]=={
        "items":[],"count":0,"open_count":0,"review_count":0,"accepted_count":0,"waived_count":0}
