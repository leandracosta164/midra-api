from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"field_reports":{"reference_id":"FIELD-1","summary":{"items":items}}},
        job_number="ENG-F1",project_name="Field",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=17,events=[])

def test_field_report_projection_counts():
    items=[{"report_id":"F1","status":"OPEN","follow_up_required":True},
           {"report_id":"F2","status":"CLOSED","follow_up_required":False}]
    f=engineering_workspace(job(items))["field_reports"]
    assert f["count"]==2 and f["open_count"]==1 and f["follow_up_count"]==1 and f["closed_count"]==1

def test_empty_field_report_register_is_explicit():
    assert engineering_workspace(job([]))["field_reports"]=={
        "items":[],"count":0,"open_count":0,"follow_up_count":0,"closed_count":0}
