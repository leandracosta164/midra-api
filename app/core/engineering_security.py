"""Authentication boundary for the internal MIDRA Engineering workplace."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.session import get_db
from app.models.engineering_session import EngineeringSession

COOKIE_NAME="midra_engineering_session"
LOCAL_ORIGINS={
    "http://localhost:4321","http://127.0.0.1:4321",
    "http://localhost:4322","http://127.0.0.1:4322",
}

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def credentials_configured() -> bool:
    return bool(settings.MIDRA_ENGINEERING_ADMIN_EMAIL and
                settings.MIDRA_ENGINEERING_ADMIN_PASSWORD)

def authenticate_credentials(email: str,password: str) -> bool:
    if not credentials_configured():
        return False
    return (
        hmac.compare_digest(email.strip().casefold(),
                            settings.MIDRA_ENGINEERING_ADMIN_EMAIL.strip().casefold())
        and hmac.compare_digest(password,settings.MIDRA_ENGINEERING_ADMIN_PASSWORD)
    )

def create_session(db: Session,email: str) -> tuple[str,EngineeringSession]:
    raw=secrets.token_urlsafe(48)
    now=datetime.now(timezone.utc)
    session=EngineeringSession(
        token_hash=_hash_token(raw),
        user_email=email.strip().casefold(),
        created_at=now,
        expires_at=now+timedelta(hours=settings.MIDRA_ENGINEERING_SESSION_HOURS),
    )
    db.add(session); db.commit(); db.refresh(session)
    return raw,session

def delete_session(db: Session,raw_token: str | None) -> None:
    if not raw_token:
        return
    obj=db.get(EngineeringSession,_hash_token(raw_token))
    if obj:
        db.delete(obj); db.commit()

def require_engineering_user(
    request: Request,
    db: Session=Depends(get_db),
    token: str | None=Cookie(default=None,alias=COOKIE_NAME),
) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="engineering workplace authentication required")
    session=db.get(EngineeringSession,_hash_token(token))
    now=datetime.now(timezone.utc)

    # SQLite used by tests may return timezone-aware columns as naive
    # datetimes. PostgreSQL preserves the timezone. Normalize defensively
    # before comparing session expiration.
    expires_at = session.expires_at if session else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if not session or expires_at <= now:
        if session:
            db.delete(session); db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="engineering workplace session expired")

    # Cookie-authenticated state-changing browser requests must come from an allowed UI origin.
    if request.method not in {"GET","HEAD","OPTIONS"}:
        origin=request.headers.get("origin")
        app_env=str(settings.APP_ENV or "").strip().lower()
        allowed=set(LOCAL_ORIGINS) if app_env in {"development","dev","local"} else set()
        for configured_origin in (settings.MIDRA_ENGINEERING_WEB_ORIGIN, settings.MIDRA_WORKPLACE_WEB_ORIGIN):
            if configured_origin:
                allowed.add(configured_origin.rstrip("/"))
        if origin and origin.rstrip("/") not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="untrusted engineering workplace origin")
    return session.user_email

