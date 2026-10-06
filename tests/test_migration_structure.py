from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_alembic_configuration_exists():
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "alembic" / "env.py").exists()

def test_source_history_migration_exists():
    migration = ROOT / "alembic" / "versions" / "20260911_01_source_history.py"
    text = migration.read_text(encoding="utf-8")
    assert '"midra_source_versions"' in text
    assert "def upgrade" in text
    assert "def downgrade" in text
