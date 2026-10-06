from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_client_response_cannot_create_engineering_job_implicitly():
    source = (ROOT / 'midra-api/app/api/property_records.py').read_text(encoding='utf-8')
    start = source.index('@public_router.post("/public/proposal-response"')
    chunk = source[start:start + 4200]
    assert 'engineering_job_created":False' in chunk or '"engineering_job_created": False' in chunk
    assert 'engineering_job_creation_eligible' in chunk
    assert 'create_from_accepted_response' not in chunk


def test_job_creation_remains_separate_engineering_authenticated_action():
    source = (ROOT / 'midra-api/app/api/engineering_property_job_creation.py').read_text(encoding='utf-8')
    assert 'Depends(require_engineering_user)' in source
    assert 'create_from_accepted_response' in source
    assert 'Property analysis remains unaccepted' in source
    assert 'property_analysis_engineer_accepted' in source
    assert 'False' in source


def test_operator_and_client_surfaces_preserve_lifecycle_separation():
    ops = (ROOT / 'midra-web/src/pages/engineering/proposals.astro').read_text(encoding='utf-8')
    client = (ROOT / 'property-web/src/pages/proposal-response.astro').read_text(encoding='utf-8')
    for token in ['Create Engineering Job', 'separate authorized action', 'Open Engineering Job']:
        assert token in ops
    for token in ['View exact proposal PDF', 'Accept Proposal', 'Decline Proposal', 'separately authorize Engineering job creation']:
        assert token in client


def test_delivery_stays_bound_to_exact_durable_pdf_and_explicit_send():
    source = (ROOT / 'midra-api/app/api/property_records.py').read_text(encoding='utf-8')
    assert 'durable proposal PDF artifact must be created before delivery' in source
    assert 'explicit_send_authorized is not True' in source
    assert 'create_client_proposal_token' in source
    assert 'response_url' in source
