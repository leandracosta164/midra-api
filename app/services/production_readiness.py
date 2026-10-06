"""Fail-closed production configuration readiness assessment for MIDRA.

This module never returns configured secret values. It evaluates whether the
runtime configuration required for secure client proposal delivery and the
internal authenticated workspaces is suitable for a production deployment.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _present(value: object) -> bool:
    return bool(str(value or "").strip())


def _strong_secret(value: object, *, minimum: int = 24) -> bool:
    return len(str(value or "")) >= minimum


def _https_origin(value: object) -> bool:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc) and not parsed.path


def _email_like(value: object) -> bool:
    text = str(value or "").strip()
    return "@" in text and not text.startswith("@") and not text.endswith("@")


def _check(name: str, ready: bool, detail: str, category: str) -> dict[str, Any]:
    return {
        "name": name,
        "category": category,
        "ready": bool(ready),
        "detail": detail,
    }


def build_production_configuration_readiness(settings: object) -> dict[str, Any]:
    """Return a redacted production-readiness assessment.

    The result intentionally reports only booleans and generic explanatory
    text. Secret values, passwords, SMTP credentials, and signing secrets are
    never included.
    """
    app_env = str(getattr(settings, "APP_ENV", "") or "").strip().lower()
    debug = bool(getattr(settings, "DEBUG", False))

    property_origins = list(getattr(settings, "PROPERTY_WEB_ORIGINS", []) or [])
    property_origins_https = bool(property_origins) and all(_https_origin(v) for v in property_origins)
    api_public_origin = getattr(settings, "MIDRA_API_PUBLIC_ORIGIN", None)
    api_allowed_hosts = [str(v).strip().lower().rstrip(".") for v in (getattr(settings, "API_ALLOWED_HOSTS", []) or []) if str(v).strip()]
    api_origin_host = (urlparse(str(api_public_origin or "").strip()).hostname or "").lower().rstrip(".")
    api_host_policy_ready = bool(api_allowed_hosts) and not any("*" in host for host in api_allowed_hosts) and bool(api_origin_host) and api_origin_host in api_allowed_hosts

    smtp_host = getattr(settings, "MIDRA_PROPOSAL_EMAIL_HOST", None)
    smtp_from = getattr(settings, "MIDRA_PROPOSAL_EMAIL_FROM", None)
    smtp_user = getattr(settings, "MIDRA_PROPOSAL_EMAIL_USERNAME", None)
    smtp_password = getattr(settings, "MIDRA_PROPOSAL_EMAIL_PASSWORD", None)
    smtp_tls = bool(getattr(settings, "MIDRA_PROPOSAL_EMAIL_USE_TLS", False))
    smtp_ssl = bool(getattr(settings, "MIDRA_PROPOSAL_EMAIL_USE_SSL", False))
    smtp_auth_consistent = (_present(smtp_user) == _present(smtp_password))
    smtp_encryption_safe = (smtp_tls != smtp_ssl)

    checks = [
        _check(
            "production_environment",
            app_env in {"production", "prod"},
            "APP_ENV identifies a production runtime.",
            "runtime",
        ),
        _check(
            "debug_disabled",
            not debug,
            "DEBUG is disabled for production.",
            "runtime",
        ),
        _check(
            "database_password_configured",
            _present(getattr(settings, "POSTGRES_PASSWORD", None)),
            "Database authentication is configured.",
            "database",
        ),
        _check(
            "engineering_admin_credentials",
            _email_like(getattr(settings, "MIDRA_ENGINEERING_ADMIN_EMAIL", None))
            and _strong_secret(getattr(settings, "MIDRA_ENGINEERING_ADMIN_PASSWORD", None), minimum=12),
            "Engineering administrative authentication is configured.",
            "authentication",
        ),
        _check(
            "property_admin_credentials",
            _email_like(getattr(settings, "MIDRA_PROPERTY_ADMIN_EMAIL", None))
            and _strong_secret(getattr(settings, "MIDRA_PROPERTY_ADMIN_PASSWORD", None), minimum=12)
            and _strong_secret(getattr(settings, "MIDRA_PROPERTY_AUTH_SECRET", None), minimum=24),
            "Property administrative authentication and session signing are configured.",
            "authentication",
        ),
        _check(
            "api_public_origin_https",
            _https_origin(api_public_origin),
            "API public origin is an HTTPS deployment origin.",
            "origins",
        ),
        _check(
            "api_host_header_policy",
            api_host_policy_ready,
            "API Host-header allowlist is explicit and contains the configured public API hostname.",
            "security",
        ),
        _check(
            "engineering_web_origin_https",
            _https_origin(getattr(settings, "MIDRA_ENGINEERING_WEB_ORIGIN", None)),
            "Engineering web origin is an HTTPS deployment origin.",
            "origins",
        ),
        _check(
            "workplace_web_origin_https",
            _https_origin(getattr(settings, "MIDRA_WORKPLACE_WEB_ORIGIN", None)),
            "Workplace web origin is an HTTPS deployment origin.",
            "origins",
        ),
        _check(
            "property_web_origins_https",
            property_origins_https,
            "All configured Property web origins are HTTPS deployment origins.",
            "origins",
        ),
        _check(
            "property_public_origin_https",
            _https_origin(getattr(settings, "MIDRA_PROPERTY_PUBLIC_ORIGIN", None)),
            "Public Property origin for signed client response links is HTTPS.",
            "origins",
        ),
        _check(
            "proposal_response_signing_secret",
            _strong_secret(getattr(settings, "MIDRA_PROPOSAL_RESPONSE_SECRET", None), minimum=24),
            "Client proposal response signing secret is configured with sufficient length.",
            "client_proposal",
        ),
        _check(
            "proposal_email_transport",
            _present(smtp_host) and _email_like(smtp_from) and smtp_auth_consistent and smtp_encryption_safe,
            "Proposal email transport is configured with a sender and exactly one encrypted SMTP mode; username/password configuration is consistent.",
            "client_proposal",
        ),
    ]

    categories: dict[str, bool] = {}
    for category in {str(item["category"]) for item in checks}:
        category_checks = [item for item in checks if item["category"] == category]
        categories[category] = all(bool(item["ready"]) for item in category_checks)

    client_delivery_ready = bool(categories.get("client_proposal")) and bool(categories.get("origins"))
    overall = all(bool(item["ready"]) for item in checks)
    return {
        "status": "READY" if overall else "NOT_READY",
        "production_ready": overall,
        "client_proposal_delivery_ready": client_delivery_ready,
        "categories": categories,
        "checks": checks,
        "redacted": True,
    }
