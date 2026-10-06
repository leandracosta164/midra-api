from pathlib import Path

from app.core.settings import settings


def test_alembic_environment_uses_application_database_url():
    env_path = Path(__file__).parents[1] / "alembic" / "env.py"
    text = env_path.read_text(encoding="utf-8")
    assert "settings.DATABASE_URL" in text
    assert "settings.DATABASE_URL.render_as_string(hide_password=False)" in text
    assert '.replace("%", "%%")' in text
    assert 'os.getenv("DATABASE_URL"' not in text


def test_database_url_rendering_preserves_password_for_alembic():
    rendered = settings.DATABASE_URL.render_as_string(hide_password=False)
    assert rendered.startswith("postgresql+psycopg://")
    assert "***" not in rendered
    assert settings.POSTGRES_USER in rendered
    assert settings.POSTGRES_DB in rendered
