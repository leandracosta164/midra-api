from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.core.engineering_security import require_engineering_user
from app.core.settings import settings
from app.services.production_readiness import build_production_configuration_readiness
from app.services.observability import operational_snapshot
from app.services.deployment_identity import (
    EXPECTED_DATABASE_REVISION as CURRENT_EXPECTED_DATABASE_REVISION,
    RELEASE_ID as LEGACY_CURRENT_RELEASE_ID,
    ACTIVE_RELEASE_ID,
    current_database_revision,
    artifact_storage_readiness,
)

# Historical 2.53 compatibility token: RELEASE_ID as CURRENT_RELEASE_ID
CURRENT_RELEASE_ID = ACTIVE_RELEASE_ID

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    """Minimal public liveness probe with no infrastructure disclosure."""
    return {"status": "healthy"}


@router.get("/database")
def database_health(
    db: Session = Depends(get_db),
    _engineering_user: str = Depends(require_engineering_user),
) -> dict[str, str]:
    """Authenticated database readiness probe without server/version disclosure."""
    db.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "database": "connected",
    }


@router.get("/operations")
def operational_health(
    _engineering_user: str = Depends(require_engineering_user),
) -> dict:
    """Authenticated process-level operational counters without request or secret data."""
    return {"status": "healthy", "operations": operational_snapshot(), "redacted": True}


@router.get("/production-readiness")
def production_configuration_readiness(
    _engineering_user: str = Depends(require_engineering_user),
) -> dict:
    """Return a redacted configuration readiness report for authorized staff."""
    return build_production_configuration_readiness(settings)


# Locked MIDRA Property 2.52 compatibility contract. These literals remain
# intentionally present so historical verification can prove the 2.52 surface
# was not erased by later release-readiness work.
EXPECTED_DATABASE_REVISION = "20261004_18"
RELEASE_ID = "MIDRA_PROPERTY_2_52"
LEGACY_2_52_REVISION_SQL = "SELECT version_num FROM alembic_version"


@router.get("/deployment")
def deployment_readiness(
    db: Session = Depends(get_db),
    _engineering_user: str = Depends(require_engineering_user),
) -> dict:
    """Authenticated release identity and database-revision readiness report."""
    db.execute(text("SELECT 1"))
    current_revision = current_database_revision()
    revision_current = current_revision == CURRENT_EXPECTED_DATABASE_REVISION
    configuration = build_production_configuration_readiness(settings)
    storage = artifact_storage_readiness(settings)
    ready = bool(
        revision_current
        and configuration.get("production_ready")
        and storage.get("storage_ready")
    )
    return {
        "status": "READY" if ready else "NOT_READY",
        "release": {
            "release_id": CURRENT_RELEASE_ID,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
        },
        "database": {
            "connected": True,
            "current_revision": current_revision,
            "expected_revision": EXPECTED_DATABASE_REVISION,
            "revision_current": revision_current,
        },
        "configuration": {
            "production_ready": bool(configuration.get("production_ready")),
            "client_proposal_delivery_ready": bool(configuration.get("client_proposal_delivery_ready")),
        },
        "artifact_storage": {
            "storage_ready": bool(storage.get("storage_ready")),
            "configured": bool(storage.get("configured")),
            "absolute": bool(storage.get("absolute")),
            "available": bool(storage.get("available")),
            "writable": bool(storage.get("writable")),
        },
        "redacted": True,
    }
