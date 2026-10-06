from pathlib import Path
import tempfile

from sqlalchemy import text

from app.db.database import engine
from app.services.production_readiness import build_production_configuration_readiness

EXPECTED_DATABASE_REVISION = "20261004_18"
RELEASE_ID = "MIDRA_PROPERTY_2_53"
# Historical 2.56 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_56"
# Historical 2.57 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_57"
# Historical 2.58 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_58"
# Historical 2.59 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_59"
# Historical 2.60 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_60"
# Historical 2.61 compatibility literal: ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_61"
ACTIVE_RELEASE_ID = "MIDRA_PROPERTY_2_62"


def current_database_revision() -> str | None:
    """Return the live Alembic revision without exposing database metadata."""
    with engine.connect() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version")).first()
    if not row or row[0] is None:
        return None
    return str(row[0])


def enforce_production_database_revision(settings: object) -> dict[str, object]:
    """Fail closed on production startup when code and DB revisions differ."""
    environment = str(getattr(settings, "APP_ENV", "") or "").strip().lower()
    if environment not in {"production", "prod"}:
        return {
            "enforced": False,
            "environment": environment or "development",
            "expected_revision": EXPECTED_DATABASE_REVISION,
        }

    current_revision = current_database_revision()
    if current_revision != EXPECTED_DATABASE_REVISION:
        raise RuntimeError(
            "MIDRA production startup refused: database revision mismatch "
            f"(current={current_revision!r}, expected={EXPECTED_DATABASE_REVISION!r})."
        )

    return {
        "enforced": True,
        "environment": environment,
        "current_revision": current_revision,
        "expected_revision": EXPECTED_DATABASE_REVISION,
    }

def enforce_production_configuration(settings: object) -> dict[str, object]:
    """Fail closed on production startup when required deployment configuration is unsafe."""
    environment = str(getattr(settings, "APP_ENV", "") or "").strip().lower()
    if environment not in {"production", "prod"}:
        return {
            "enforced": False,
            "environment": environment or "development",
        }

    readiness = build_production_configuration_readiness(settings)
    if not bool(readiness.get("production_ready")):
        failed_checks = [
            str(item.get("name") or "unknown")
            for item in list(readiness.get("checks") or [])
            if not bool(item.get("ready"))
        ]
        failed_summary = ",".join(failed_checks) or "unknown"
        raise RuntimeError(
            "MIDRA production startup refused: production configuration is not ready "
            f"(failed_checks={failed_summary})."
        )

    return {
        "enforced": True,
        "environment": environment,
        "production_ready": True,
    }


def artifact_storage_readiness(settings: object) -> dict[str, object]:
    """Return redacted Engineering artifact-storage readiness without exposing its path."""
    configured = str(getattr(settings, "MIDRA_ENGINEERING_FILE_ROOT", "") or "").strip()
    if not configured:
        return {"storage_ready": False, "configured": False, "absolute": False, "available": False, "writable": False}

    root = Path(configured).expanduser()
    absolute = root.is_absolute()
    available = bool(absolute and root.exists() and root.is_dir())
    writable = False
    probe_path: Path | None = None
    if available:
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".midra_storage_probe_",
                dir=root,
                delete=False,
            ) as probe:
                probe.write(b"MIDRA")
                probe.flush()
                probe_path = Path(probe.name)
            writable = True
        except OSError:
            writable = False
        finally:
            if probe_path is not None:
                try:
                    probe_path.unlink(missing_ok=True)
                except OSError:
                    pass

    return {
        "storage_ready": bool(configured and absolute and available and writable),
        "configured": True,
        "absolute": absolute,
        "available": available,
        "writable": writable,
    }


def enforce_production_artifact_storage(settings: object) -> dict[str, object]:
    """Fail closed in production unless Engineering artifact storage is durable and writable."""
    environment = str(getattr(settings, "APP_ENV", "") or "").strip().lower()
    if environment not in {"production", "prod"}:
        return {
            "enforced": False,
            "environment": environment or "development",
        }

    readiness = artifact_storage_readiness(settings)
    if not bool(readiness.get("configured")):
        raise RuntimeError(
            "MIDRA production startup refused: Engineering artifact storage is not configured."
        )
    if not bool(readiness.get("absolute")):
        raise RuntimeError(
            "MIDRA production startup refused: Engineering artifact storage must use an absolute path."
        )
    if not bool(readiness.get("available")):
        raise RuntimeError(
            "MIDRA production startup refused: Engineering artifact storage directory is unavailable."
        )
    if not bool(readiness.get("writable")):
        raise RuntimeError(
            "MIDRA production startup refused: Engineering artifact storage is not writable."
        )

    return {
        "enforced": True,
        "environment": environment,
        "storage_ready": True,
    }
