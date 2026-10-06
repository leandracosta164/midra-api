from types import SimpleNamespace
from app.services.engineering_workplace_portfolio import _workplace_analysis_evidence_change_comparison


def test_compares_recorded_evidence_metadata_only():
    selected=SimpleNamespace(
        analysis_run_id='a1',
        analysis={
            'verification_items':[{'code':'VERIFY_A'}],
            'sources':[{'source_url':'https://example.com/a','label':'A'}],
        },
    )
    latest=SimpleNamespace(
        analysis_run_id='a2',
        analysis={
            'verification_items':[{'code':'VERIFY_A'},{'code':'VERIFY_B'}],
            'sources':[{'source_url':'https://example.com/a','label':'A'},{'source_url':'https://example.com/b','label':'B'}],
            'dynamic_intelligence':{'dynamic_promotable':False},
        },
    )
    result=_workplace_analysis_evidence_change_comparison(selected_run=selected,latest_run=latest)
    assert result['is_latest'] is False
    assert result['selected']['verification_item_count']==1
    assert result['latest']['verification_item_count']==2
    assert result['selected']['recorded_source_count']==1
    assert result['latest']['recorded_source_count']==2
    assert result['comparison_mode']=='RECORDED_EVIDENCE_METADATA_ONLY'
    assert 'verification_item_count' in result['changed_fields']
    assert 'recorded_source_count' in result['changed_fields']
