from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_engineering_proposal_queue_is_engineering_authenticated():
    source=(ROOT/'midra-api/app/api/property_records.py').read_text(encoding='utf-8')
    start=source.index('@public_router.get("/engineering/proposal-requests"')
    chunk=source[start:start+2200]
    assert 'Depends(require_engineering_user)' in chunk
    assert 'list_all_by_status' in chunk
    assert 'classify_property_engineering_proposal_lifecycle' in chunk

def test_workspace_preserves_separate_authorized_actions():
    source=(ROOT/'midra-web/src/pages/engineering/proposals.astro').read_text(encoding='utf-8')
    for token in [
        'Generate private draft', 'Approve exact draft', 'Authorize client release',
        'Create durable exact PDF', 'explicit_send_authorized:true',
        'Record explicit client response', 'Create Engineering Job'
    ]:
        assert token in source
    assert 'automatic_send' not in source
