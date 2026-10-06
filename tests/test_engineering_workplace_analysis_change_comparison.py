from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import _workplace_analysis_change_comparison

def test_compares_recorded_analysis_metadata_only():
    selected=SimpleNamespace(analysis_run_id='a1',requested_work='Deck',intelligence_status='VERIFY',created_at=None)
    latest=SimpleNamespace(analysis_run_id='a2',requested_work='Addition',intelligence_status='READY',created_at=None)
    result=_workplace_analysis_change_comparison(selected_run=selected,latest_run=latest,proposals_by_analysis={'a1':[{}],'a2':[{},{}]},jobs_by_analysis={'a1':[],'a2':[{}]})
    assert result['is_latest'] is False
    assert set(result['changed_fields'])=={'requested_work','intelligence_status','proposal_count','engineering_job_count'}
    assert result['comparison_mode']=='RECORDED_METADATA_ONLY'
