from types import SimpleNamespace
from app.services import engineering_workplace_portfolio as workplace

class Scalars:
    def __init__(self, first=None, all_items=None):
        self._first=first
        self._all=list(all_items or [])
    def first(self): return self._first
    def all(self): return self._all

class Result:
    def __init__(self, first=None, all_items=None): self._s=Scalars(first,all_items)
    def scalars(self): return self._s

class FakeDB:
    def __init__(self, creation, link, prop, request):
        self.creation=creation; self.link=link; self.prop=prop; self.request=request; self.calls=0
    def execute(self, stmt):
        self.calls+=1
        if self.calls==1: return Result(first=self.creation)
        if self.calls==2: return Result(all_items=[self.link])
        if self.calls==3: return Result(all_items=[self.prop])
        raise AssertionError("unexpected query")
    def get(self, model, key):
        name=model.__name__
        if name=="PropertyEngineeringProposalRequest": return self.request
        if name=="PropertyRecord": return self.prop
        return None

def test_job_detail_combines_engineering_workspace_and_property_lineage(monkeypatch):
    monkeypatch.setattr(workplace,"load_engineering_workspace",lambda db,job:{
        "job_number":job,"project_name":"Pool Engineering","project_health":{"state":"ON_TRACK"},
        "attention_summary":{"count":0,"high_count":0,"items":[]},"project_brief":{"summary_lines":["Ready."]},
    })
    creation=SimpleNamespace(
        proposal_request_id="r1",property_record_id="p1",proposal_number="P-001",
        engineering_job_creation_id="jc1",created_by="eng@example.com",created_at=None,
    )
    link=SimpleNamespace(
        link_id="l1",property_record_id="p1",link_status="linked",notes=None,
        created_by="eng@example.com",created_at=None,
    )
    prop=SimpleNamespace(
        property_record_id="p1",display_address="1 Main St",search_query="1 Main St",
        municipality="Howell",county="Monmouth",block="1",lot="2",intelligence_status="MIDRA_ANALYSIS",
    )
    request=SimpleNamespace(analysis_run_id="a1",project_goal="pool")
    data=workplace.engineering_workplace_job_detail(FakeDB(creation,link,prop,request),"26-001")
    assert data["status"]=="MIDRA_WORKPLACE_JOB_DETAIL_READY"
    assert data["workspace"]["job_number"]=="26-001"
    assert data["property_origin"]["proposal_request_id"]=="r1"
    assert data["property_origin"]["property"]["address"]=="1 Main St"
    assert data["linked_properties"][0]["is_origin_property"] is True
    assert data["professional_boundary"]["automatic_professional_action"] is False

def test_property_identity_is_read_only_summary():
    prop=SimpleNamespace(property_record_id="p1",display_address="1 Main St",search_query="x",municipality="Howell",county="Monmouth",block="1",lot="2",intelligence_status="MIDRA_ANALYSIS")
    row=workplace._workplace_property_identity(prop)
    assert row["property_record_id"]=="p1"
    assert row["address"]=="1 Main St"
    assert "latest_analysis" not in row
