from types import SimpleNamespace
from app.services.engineering_workspace_dashboard import engineering_workspace

def job(items):
    return SimpleNamespace(sections={"rfis":{"reference_id":"RFI-1","summary":{"items":items}}},
        job_number="ENG-RFI1",project_name="RFI",project_type="SITE",source="TEST",
        property_address="1 Project Way",client_id="CLIENT-1",state="ACTIVE",version=17,events=[])

def test_rfi_projection_counts():
    items=[{"rfi_id":"R1","status":"OPEN","priority":"URGENT"},
           {"rfi_id":"R2","status":"ANSWERED","priority":"NORMAL"},
           {"rfi_id":"R3","status":"CLOSED","priority":"HIGH"}]
    r=engineering_workspace(job(items))["rfis"]
    assert r["count"]==3 and r["open_count"]==1 and r["answered_count"]==1
    assert r["closed_count"]==1 and r["urgent_count"]==1

def test_empty_rfi_register_is_explicit():
    assert engineering_workspace(job([]))["rfis"]=={
        "items":[],"count":0,"open_count":0,"answered_count":0,"closed_count":0,"urgent_count":0}
