from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"meetings":{"reference_id":"MEET-1","summary":{"items":items}}},
        job_number="ENG-MTG",project_name="Meetings",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=17,events=[])

def test_meeting_register_projects_counts():
    m=engineering_workspace(job([{"meeting_id":"M1","status":"SCHEDULED"},{"meeting_id":"M2","status":"COMPLETED"}]))["meetings"]
    assert m["count"]==2 and m["scheduled_count"]==1 and m["completed_count"]==1

def test_empty_meeting_register_is_explicit():
    assert engineering_workspace(job([]))["meetings"]=={"items":[],"count":0,"scheduled_count":0,"completed_count":0}
