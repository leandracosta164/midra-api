"""Authentication boundary for the MIDRA Property workspace."""
from __future__ import annotations

from datetime import datetime, timezone
import base64
import hashlib
import hmac
import json
import secrets

from fastapi import Cookie, HTTPException, Request, status

from app.core.settings import settings

COOKIE_NAME = "midra_property_session"
TOKEN_VERSION = 1


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def credentials_configured() -> bool:
    return bool(
        settings.MIDRA_PROPERTY_ADMIN_EMAIL
        and settings.MIDRA_PROPERTY_ADMIN_PASSWORD
        and settings.MIDRA_PROPERTY_AUTH_SECRET
    )


def authenticate_credentials(email: str, password: str) -> bool:
    if not credentials_configured():
        return False
    return (
        hmac.compare_digest(
            email.strip().casefold(),
            settings.MIDRA_PROPERTY_ADMIN_EMAIL.strip().casefold(),
        )
        and hmac.compare_digest(password, settings.MIDRA_PROPERTY_ADMIN_PASSWORD)
    )


def create_session_token(email: str, *, now: datetime | None = None) -> str:
    if not settings.MIDRA_PROPERTY_AUTH_SECRET:
        raise RuntimeError("MIDRA Property authentication secret is not configured")
    issued = now or datetime.now(timezone.utc)
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=timezone.utc)
    payload = {
        "v": TOKEN_VERSION,
        "email": email.strip().casefold(),
        "iat": int(issued.timestamp()),
        "exp": int(issued.timestamp()) + settings.MIDRA_PROPERTY_SESSION_HOURS * 3600,
        "nonce": secrets.token_urlsafe(12),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(
        settings.MIDRA_PROPERTY_AUTH_SECRET.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{body}.{_b64encode(signature)}"


def resolve_session_token(token: str | None, *, now: datetime | None = None) -> str | None:
    if not token or not settings.MIDRA_PROPERTY_AUTH_SECRET:
        return None
    try:
        body, signature_text = token.split(".", 1)
        expected = hmac.new(
            settings.MIDRA_PROPERTY_AUTH_SECRET.encode("utf-8"),
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()
        supplied = _b64decode(signature_text)
        if not hmac.compare_digest(expected, supplied):
            return None
        payload = json.loads(_b64decode(body))
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        if payload.get("v") != TOKEN_VERSION:
            return None
        if int(payload.get("exp", 0)) <= int(current.timestamp()):
            return None
        email = str(payload.get("email") or "").strip().casefold()
        return email or None
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def require_property_user(
    request: Request,
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str:
    email = resolve_session_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="property workspace authentication required",
        )

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        allowed = set(settings.PROPERTY_WEB_ORIGINS)
        if origin and origin.rstrip("/") not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="untrusted property workspace origin",
            )
    return email
