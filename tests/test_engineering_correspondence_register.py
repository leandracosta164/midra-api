from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(
        sections={"correspondence":{"reference_id":"CORR-1","summary":{"items":items}}},
        job_number="ENG-140",project_name="Correspondence Register",
        project_type="SITE",source="TEST",property_address="1 Project Way",
        client_id="CLIENT-1",state="ACTIVE",version=14,events=[]
    )

def test_correspondence_register_projects_recorded_items_and_counts():
    items=[
        {"correspondence_id":"C-1","direction":"INBOUND","subject":"Agency comment",
         "response_required":True,"response_status":"PENDING"},
        {"correspondence_id":"C-2","direction":"OUTBOUND","subject":"Client update",
         "response_required":False,"response_status":"NOT_REQUIRED"},
        {"correspondence_id":"C-3","direction":"INBOUND","subject":"Survey response",
         "response_required":True,"response_status":"RESPONDED"},
    ]
    w=engineering_workspace(job(items))
    c=w["correspondence"]
    assert c["items"]==items
    assert c["count"]==3
    assert c["inbound_count"]==2
    assert c["outbound_count"]==1
    assert c["response_required_count"]==1
    assert w["connected_sections"]["correspondence"]=="CORR-1"

def test_correspondence_register_is_empty_when_no_records_exist():
    w=engineering_workspace(job([]))
    assert w["correspondence"]=={
        "items":[],"count":0,"inbound_count":0,"outbound_count":0,"response_required_count":0
    }

def test_correspondence_projection_does_not_change_professional_controls():
    w=engineering_workspace(job([]))
    assert w["controls"]["professional_actions_require_approval"] is True
    assert w["controls"]["automatic_professional_completion"] is False
    assert w["controls"]["automatic_issue_or_submission"] is False
