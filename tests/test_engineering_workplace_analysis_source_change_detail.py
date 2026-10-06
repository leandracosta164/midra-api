from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import _workplace_analysis_source_change_detail


def test_compares_recorded_source_references_only():
    selected=SimpleNamespace(
        analysis_run_id='a1',
        analysis={
            'sources':[
                {'source_url':'https://example.com/shared','label':'Shared','source_type':'MUNICIPAL'},
                {'source_url':'https://example.com/old','label':'Old source','source_type':'MUNICIPAL','authority':'LOCAL'},
            ],
        },
    )
    latest=SimpleNamespace(
        analysis_run_id='a2',
        analysis={
            'sources':[
                {'source_url':'https://example.com/shared','label':'Shared','source_type':'MUNICIPAL'},
                {'source_url':'https://example.com/new','label':'New source','source_type':'STATE','authority':'STATE'},
            ],
        },
    )
    result=_workplace_analysis_source_change_detail(selected_run=selected,latest_run=latest)
    assert result['is_latest'] is False
    assert result['comparison_mode']=='RECORDED_SOURCE_REFERENCES_ONLY'
    assert result['added_source_count']==1
    assert result['removed_source_count']==1
    assert result['added_sources'][0]['source_url']=='https://example.com/new'
    assert result['removed_sources'][0]['source_url']=='https://example.com/old'


def test_latest_run_has_no_source_delta():
    run=SimpleNamespace(
        analysis_run_id='a2',
        analysis={'sources':[{'source_url':'https://example.com/a','label':'A'}]},
    )
    result=_workplace_analysis_source_change_detail(selected_run=run,latest_run=run)
    assert result['is_latest'] is True
    assert result['added_source_count']==0
    assert result['removed_source_count']==0
