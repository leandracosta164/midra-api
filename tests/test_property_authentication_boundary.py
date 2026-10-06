from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from starlette.requests import Request

from app.core import property_security
from app.core.settings import settings


def configure(monkeypatch):
    monkeypatch.setattr(settings, "MIDRA_PROPERTY_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setattr(settings, "MIDRA_PROPERTY_ADMIN_PASSWORD", "secret-password")
    monkeypatch.setattr(settings, "MIDRA_PROPERTY_AUTH_SECRET", "test-secret-that-is-long-enough")
    monkeypatch.setattr(settings, "MIDRA_PROPERTY_SESSION_HOURS", 12)
    monkeypatch.setattr(
        settings,
        "MIDRA_PROPERTY_WEB_ORIGINS",
        "http://localhost:4322,https://property.example.com",
    )


def request(method="GET", origin=None):
    headers=[]
    if origin:
        headers.append((b"origin", origin.encode("utf-8")))
    return Request({"type":"http","method":method,"path":"/","headers":headers})


def test_property_credentials_are_separate_and_configurable(monkeypatch):
    configure(monkeypatch)
    assert property_security.credentials_configured() is True
    assert property_security.authenticate_credentials("OWNER@example.com","secret-password") is True
    assert property_security.authenticate_credentials("owner@example.com","wrong") is False


def test_property_session_token_is_signed_and_expires(monkeypatch):
    configure(monkeypatch)
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    token=property_security.create_session_token("owner@example.com",now=now)
    assert property_security.resolve_session_token(token,now=now+timedelta(hours=1))=="owner@example.com"
    assert property_security.resolve_session_token(token,now=now+timedelta(hours=13)) is None
    body,sig=token.split(".",1)
    tampered=body[:-1]+("A" if body[-1]!="A" else "B")+"."+sig
    assert property_security.resolve_session_token(tampered,now=now) is None


def test_state_change_origin_is_checked(monkeypatch):
    configure(monkeypatch)
    now=datetime.now(timezone.utc)
    token=property_security.create_session_token("owner@example.com",now=now)
    assert property_security.require_property_user(
        request("POST","https://property.example.com"),
        token,
    )=="owner@example.com"
    try:
        property_security.require_property_user(
            request("POST","https://untrusted.example.com"),
            token,
        )
    except HTTPException as exc:
        assert exc.status_code==403
    else:
        raise AssertionError("untrusted origin must be rejected")


def test_missing_property_session_fails_closed(monkeypatch):
    configure(monkeypatch)
    try:
        property_security.require_property_user(request(),None)
    except HTTPException as exc:
        assert exc.status_code==401
    else:
        raise AssertionError("missing Property session must be rejected")
