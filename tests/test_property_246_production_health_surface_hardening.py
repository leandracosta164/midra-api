from pathlib import Path


def health_source() -> str:
    return Path('app/api/health.py').read_text(encoding='utf-8')


def test_public_liveness_is_minimal_and_non_database():
    source=health_source()
    assert '@router.get("/live")' in source
    assert 'def liveness()' in source
    assert 'return {"status": "healthy"}' in source


def test_database_health_requires_engineering_auth_and_redacts_server_version():
    source=health_source()
    assert '@router.get("/database")' in source
    assert '_engineering_user: str = Depends(require_engineering_user)' in source
    assert 'SELECT 1' in source
    assert 'SELECT version()' not in source
    assert '"server"' not in source
