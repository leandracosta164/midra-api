from types import SimpleNamespace
from app.services import engineering_workplace_portfolio as workplace

class Scalars:
    def __init__(self, first=None, all_items=None): self._first=first; self._all=list(all_items or [])
    def first(self): return self._first
    def all(self): return self._all
class Result:
    def __init__(self, first=None, all_items=None): self._s=Scalars(first,all_items)
    def scalars(self): return self._s
class FakeDB:
    def __init__(self, creation, link, prop, request): self.creation=creation; self.link=link; self.prop=prop; self.request=request; self.calls=0
    def execute(self, stmt):
        self.calls+=1
        if self.calls==1: return Result(first=self.creation)
        if self.calls==2: return Result(all_items=[self.link])
        if self.calls==3: return Result(all_items=[self.prop])
        raise AssertionError("unexpected query")
    def get(self, model, key):
        if model.__name__=="PropertyEngineeringProposalRequest": return self.request
        if model.__name__=="PropertyRecord": return self.prop
        return None

def test_job_lineage_has_workplace_navigation(monkeypatch):
    monkeypatch.setattr(workplace,"load_engineering_workspace",lambda db,job:{"job_number":job})
    creation=SimpleNamespace(proposal_request_id="r1",property_record_id="p1",proposal_number="P-001",engineering_job_creation_id="jc1",created_by="eng@example.com",created_at=None)
    link=SimpleNamespace(link_id="l1",property_record_id="p1",link_status="linked",notes=None,created_by="eng@example.com",created_at=None)
    prop=SimpleNamespace(property_record_id="p1",display_address="1 Main St",search_query="1 Main St",municipality="Howell",county="Monmouth",block="1",lot="2",intelligence_status="MIDRA_ANALYSIS")
    request=SimpleNamespace(analysis_run_id="a1",project_goal="pool")
    data=workplace.engineering_workplace_job_detail(FakeDB(creation,link,prop,request),"26-001")
    assert data["property_origin"]["proposal_href"]=="proposal.html?proposal_request_id=r1"
    assert data["property_origin"]["property_href"]=="property.html?property_record_id=p1"
    assert data["property_origin"]["evidence_href"]=="evidence.html?property_record_id=p1"
    assert data["linked_properties"][0]["property_href"]=="property.html?property_record_id=p1"
    assert data["linked_properties"][0]["evidence_href"]=="evidence.html?property_record_id=p1"
