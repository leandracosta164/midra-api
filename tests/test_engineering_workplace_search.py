from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import engineering_workplace_search

class Scalars:
    def __init__(self, items): self.items=list(items)
    def all(self): return self.items

class Result:
    def __init__(self, *, scalar_items=None, rows=None):
        self._scalar_items=list(scalar_items or [])
        self._rows=list(rows or [])
    def scalars(self): return Scalars(self._scalar_items)
    def all(self): return self._rows

class FakeDB:
    def __init__(self, prop, request, draft, job):
        self.prop=prop; self.request=request; self.draft=draft; self.job=job; self.calls=0
    def execute(self, stmt):
        self.calls+=1
        if self.calls==1: return Result(scalar_items=[self.prop])
        if self.calls==2: return Result(rows=[(self.request,self.prop,self.draft)])
        if self.calls==3: return Result(scalar_items=[self.job])
        raise AssertionError("unexpected query")

def fixtures():
    prop=SimpleNamespace(property_record_id="p1",display_address="1 Main Street",search_query="1 Main Street",municipality="Howell",county="Monmouth",block="145",lot="22",updated_at=None)
    request=SimpleNamespace(proposal_request_id="r1",property_record_id="p1",analysis_run_id="a1",project_goal="Pool and patio",customer_name="Jane Smith",customer_email="jane@example.com",created_at=None)
    draft=SimpleNamespace(proposal_number="P-2026-001")
    job=SimpleNamespace(job_number="26-001",project_name="Main Street Pool",project_type="Residential",property_address="1 Main Street",client_id="C-1",state="ACTIVE",updated_at=None)
    return prop,request,draft,job

def test_search_returns_property_proposal_and_engineering_job():
    prop,request,draft,job=fixtures()
    data=engineering_workplace_search(FakeDB(prop,request,draft,job),"Main",limit=12)
    assert data["status"]=="MIDRA_WORKPLACE_SEARCH_READY"
    kinds={item["kind"] for item in data["results"]}
    assert kinds=={"PROPERTY","PROPOSAL","ENGINEERING_JOB"}
    assert any(item.get("proposal_request_id")=="r1" for item in data["results"])
    assert any(item.get("engineering_job_number")=="26-001" for item in data["results"])
    assert data["professional_boundary"]["automatic_professional_action"] is False

def test_short_query_does_not_touch_database():
    class NoDB:
        def execute(self, stmt): raise AssertionError("database should not be queried")
    data=engineering_workplace_search(NoDB(),"x")
    assert data["results"]==[]
    assert data["result_count"]==0

def test_limit_is_bounded():
    prop,request,draft,job=fixtures()
    data=engineering_workplace_search(FakeDB(prop,request,draft,job),"Main",limit=1000)
    assert len(data["results"])<=25
