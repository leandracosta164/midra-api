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
    def __init__(self, record, analysis, request, link, job): self.record=record; self.analysis=analysis; self.request=request; self.link=link; self.job=job; self.calls=0
    def get(self, model, key):
        n=model.__name__
        if n=='PropertyRecord': return self.record
        if n=='EngineeringJob': return self.job
        return None
    def execute(self, stmt):
        self.calls+=1
        if self.calls==1:return Result(first=self.analysis)
        if self.calls==2:return Result(all_items=[self.request])
        if self.calls in (3,4,5,6,7):return Result(first=None)
        if self.calls==8:return Result(all_items=[self.link])
        raise AssertionError(self.calls)

def test_property_detail_combines_property_proposals_and_jobs(monkeypatch):
    monkeypatch.setattr(workplace,'build_delivery_verification_summary',lambda a:{'status':'VERIFY'})
    monkeypatch.setattr(workplace,'build_dynamic_engineering_handoff_summary',lambda a:{'status':'READY'})
    record=SimpleNamespace(property_record_id='p1',display_address='1 Main St',search_query='1 Main St',municipality='Howell',county='Monmouth',block='1',lot='2',intelligence_status='MIDRA_ANALYSIS')
    analysis=SimpleNamespace(analysis_run_id='a1',requested_work='pool',intelligence_status='MIDRA_ANALYSIS',analysis={},created_at=None)
    request=SimpleNamespace(proposal_request_id='r1',analysis_run_id='a1',project_goal='pool',customer_name='Client',request_status='REQUESTED',created_at=None)
    link=SimpleNamespace(link_id='l1',engineering_job_number='26-001',created_at=None)
    job=SimpleNamespace(project_name='Pool Engineering',project_type='Residential',state='ACTIVE')
    data=workplace.engineering_workplace_property_detail(FakeDB(record,analysis,request,link,job),'p1')
    assert data['status']=='MIDRA_WORKPLACE_PROPERTY_DETAIL_READY'
    assert data['property']['address']=='1 Main St'
    assert data['proposal_count']==1
    assert data['proposals'][0]['href']=='proposal.html?proposal_request_id=r1'
    assert data['linked_engineering_jobs'][0]['href']=='job.html?job=26-001'
    assert data['professional_boundary']['automatic_professional_action'] is False
