from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(
        sections={"client_portal":{"reference_id":"PORTAL-1","summary":{"items":items}}},
        job_number="ENG-142",project_name="Client Portal",
        project_type="SITE",source="TEST",property_address="1 Project Way",
        client_id="CLIENT-1",state="ACTIVE",version=14,events=[]
    )

def test_client_portal_projects_recorded_items_and_pending_client_counts():
    items=[
        {"portal_item_id":"P-1","status":"SHARED","acknowledgement_required":True,
         "acknowledgement_status":"PENDING","client_action_required":False},
        {"portal_item_id":"P-2","status":"PUBLISHED","acknowledgement_required":False,
         "client_action_required":True,"client_action_status":"PENDING"},
        {"portal_item_id":"P-3","status":"AVAILABLE","acknowledgement_required":True,
         "acknowledgement_status":"ACKNOWLEDGED","client_action_required":True,
         "client_action_status":"COMPLETED"},
    ]
    p=engineering_workspace(job(items))["client_portal"]
    assert p["items"]==items
    assert p["count"]==3
    assert p["shared_count"]==3
    assert p["acknowledgement_required_count"]==1
    assert p["client_action_required_count"]==1

def test_client_portal_keeps_connected_section_reference():
    w=engineering_workspace(job([]))
    assert w["connected_sections"]["client_portal"]=="PORTAL-1"
    assert w["client_portal"]=={
        "items":[],"count":0,"shared_count":0,
        "acknowledgement_required_count":0,"client_action_required_count":0
    }

def test_client_portal_projection_does_not_publish_or_invent_client_actions():
    items=[{"portal_item_id":"P-1","status":"DRAFT"}]
    p=engineering_workspace(job(items))["client_portal"]
    assert p["items"]==items
    assert p["shared_count"]==0
    assert p["acknowledgement_required_count"]==0
    assert p["client_action_required_count"]==0
