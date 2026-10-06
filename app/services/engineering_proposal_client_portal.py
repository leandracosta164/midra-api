"""Signed client self-service access for exact released Property-origin proposals."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_client_proposal_token(*, secret: str, property_record_id: str, proposal_request_id: str,
                                 engineering_release_id: str, recipient: str, ttl_seconds: int = 60*60*24*30,
                                 now: int | None = None) -> str:
    key=str(secret or "").encode("utf-8")
    if len(key) < 24:
        raise ValueError("proposal response signing secret must be configured and at least 24 characters")
    issued=int(time.time() if now is None else now)
    payload={
        "v":1,"property_record_id":str(property_record_id),"proposal_request_id":str(proposal_request_id),
        "engineering_release_id":str(engineering_release_id),"recipient":str(recipient or "").strip().lower(),
        "iat":issued,"exp":issued+int(ttl_seconds),
    }
    body=_b64(json.dumps(payload,separators=(",",":"),sort_keys=True).encode("utf-8"))
    sig=_b64(hmac.new(key,body.encode("ascii"),hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_client_proposal_token(*, token: str, secret: str, property_record_id: str, proposal_request_id: str,
                                 engineering_release_id: str, recipient: str, now: int | None = None) -> dict[str,Any]:
    key=str(secret or "").encode("utf-8")
    if len(key) < 24:
        raise ValueError("proposal response signing secret is not configured")
    try:
        body,sig=str(token or "").split(".",1)
        expected=_b64(hmac.new(key,body.encode("ascii"),hashlib.sha256).digest())
        if not hmac.compare_digest(sig,expected):
            raise ValueError("proposal response link is invalid")
        payload=json.loads(_unb64(body).decode("utf-8"))
    except (ValueError,TypeError,json.JSONDecodeError,UnicodeDecodeError) as exc:
        if isinstance(exc,ValueError) and str(exc).startswith("proposal response"):
            raise
        raise ValueError("proposal response link is invalid") from exc
    expected_identity={
        "property_record_id":str(property_record_id),"proposal_request_id":str(proposal_request_id),
        "engineering_release_id":str(engineering_release_id),"recipient":str(recipient or "").strip().lower(),
    }
    for key_name,value in expected_identity.items():
        if str(payload.get(key_name) or "") != value:
            raise ValueError("proposal response link does not match this proposal")
    current=int(time.time() if now is None else now)
    if int(payload.get("exp") or 0) < current:
        raise ValueError("proposal response link has expired")
    return payload
