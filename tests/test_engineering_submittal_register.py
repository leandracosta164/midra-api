from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"submittals":{"reference_id":"SUB-1","summary":{"items":items}}},
        job_number="ENG-S1",project_name="Submittals",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=17,events=[])

def test_submittal_projection_counts():
    items=[{"submittal_id":"S1","status":"RECEIVED"},{"submittal_id":"S2","status":"UNDER_REVIEW"},
           {"submittal_id":"S3","status":"APPROVED"},{"submittal_id":"S4","status":"REVISE_RESUBMIT"},
           {"submittal_id":"S5","status":"CLOSED"}]
    s=engineering_workspace(job(items))["submittals"]
    assert s["count"]==5 and s["pending_count"]==2 and s["approved_count"]==1
    assert s["revise_count"]==1 and s["closed_count"]==1

def test_empty_submittal_register_is_explicit():
    assert engineering_workspace(job([]))["submittals"]=={
        "items":[],"count":0,"pending_count":0,"approved_count":0,"revise_count":0,"closed_count":0}
