from types import SimpleNamespace

import pytest

from app.services import engineering_workplace_portfolio as workplace


class Scalars:
    def __init__(self, all_items=None):
        self._all=list(all_items or [])
    def all(self):
        return list(self._all)
    def first(self):
        return self._all[0] if self._all else None


class Result:
    def __init__(self, all_items=None):
        self._s=Scalars(all_items)
    def scalars(self):
        return self._s


class FakeDB:
    def __init__(self, record, analyses):
        self.record=record
        self.analyses=analyses
        self.calls=0
    def get(self, model, key):
        if model.__name__ == 'PropertyRecord':
            return self.record
        return None
    def execute(self, stmt):
        self.calls += 1
        if self.calls == 1:
            return Result(self.analyses)
        if self.calls in (2,3):
            return Result([])
        raise AssertionError(self.calls)


def _record():
    return SimpleNamespace(
        property_record_id='p1', display_address='1 Main St', search_query='1 Main St',
        municipality='Howell', county='Monmouth', block='1', lot='2',
        intelligence_status='MIDRA_ANALYSIS',
    )


def _analyses():
    return [
        SimpleNamespace(analysis_run_id='a2', requested_work='deck', intelligence_status='MIDRA_ANALYSIS', analysis={'id':2}, created_at=None),
        SimpleNamespace(analysis_run_id='a1', requested_work='pool', intelligence_status='MIDRA_ANALYSIS', analysis={'id':1}, created_at=None),
    ]


def test_property_detail_defaults_latest_and_can_select_historical(monkeypatch):
    monkeypatch.setattr(workplace,'build_delivery_verification_summary',lambda a:{'analysis':a.get('id')})
    monkeypatch.setattr(workplace,'build_dynamic_engineering_handoff_summary',lambda a:{'analysis':a.get('id')})
    latest=workplace.engineering_workplace_property_detail(FakeDB(_record(),_analyses()),'p1')
    assert latest['analysis']['analysis_run_id']=='a2'
    assert latest['analysis_history_count']==2
    assert latest['analysis_history'][0]['selected'] is True
    historical=workplace.engineering_workplace_property_detail(FakeDB(_record(),_analyses()),'p1','a1')
    assert historical['analysis']['analysis_run_id']=='a1'
    assert historical['analysis']['verification_summary']=={'analysis':1}
    assert historical['analysis']['evidence_href'].endswith('analysis_run_id=a1')
    assert historical['analysis_history'][1]['selected'] is True


def test_property_detail_rejects_analysis_from_outside_property():
    with pytest.raises(KeyError):
        workplace.engineering_workplace_property_detail(FakeDB(_record(),_analyses()),'p1','missing')
