from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"change_orders":{"reference_id":"CO-1","summary":{"items":items}}},
        job_number="ENG-CO1",project_name="Changes",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=18,events=[])

def test_change_order_projection_counts():
    items=[{"change_id":"C1","status":"PROPOSED"},{"change_id":"C2","status":"UNDER_REVIEW"},
           {"change_id":"C3","status":"APPROVED"},{"change_id":"C4","status":"REJECTED"},
           {"change_id":"C5","status":"IMPLEMENTED"}]
    c=engineering_workspace(job(items))["change_orders"]
    assert c["count"]==5 and c["pending_count"]==2 and c["approved_count"]==1
    assert c["rejected_count"]==1 and c["implemented_count"]==1

def test_empty_change_order_register_is_explicit():
    assert engineering_workspace(job([]))["change_orders"]=={
        "items":[],"count":0,"pending_count":0,"approved_count":0,"rejected_count":0,"implemented_count":0}
