from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(
        sections={"billing":{"reference_id":"BILL-1","summary":{"items":items}}},
        job_number="ENG-141",project_name="Billing Register",
        project_type="SITE",source="TEST",property_address="1 Project Way",
        client_id="CLIENT-1",state="ACTIVE",version=14,events=[]
    )

def test_billing_register_projects_recorded_items_and_status_counts():
    items=[
        {"billing_id":"B-1","status":"DRAFT","description":"Progress invoice"},
        {"billing_id":"B-2","status":"ISSUED","description":"Survey invoice"},
        {"billing_id":"B-3","status":"OVERDUE","description":"Design invoice"},
        {"billing_id":"B-4","status":"PAID","description":"Retainer"},
    ]
    w=engineering_workspace(job(items))
    b=w["billing"]
    assert b["items"]==items
    assert b["count"]==4
    assert b["open_count"]==3
    assert b["overdue_count"]==1
    assert b["paid_count"]==1
    assert w["connected_sections"]["billing"]=="BILL-1"

def test_billing_register_is_empty_when_no_records_exist():
    w=engineering_workspace(job([]))
    assert w["billing"]=={
        "items":[],"count":0,"open_count":0,"overdue_count":0,"paid_count":0
    }

def test_billing_projection_does_not_calculate_or_invent_money():
    items=[{"billing_id":"B-1","status":"OPEN"}]
    b=engineering_workspace(job(items))["billing"]
    assert set(b)=={"items","count","open_count","overdue_count","paid_count"}
    assert b["items"][0]==items[0]
