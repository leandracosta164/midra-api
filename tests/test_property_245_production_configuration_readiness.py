from types import SimpleNamespace

from app.services.production_readiness import build_production_configuration_readiness


def cfg(**overrides):
    base = dict(
        APP_ENV="production", DEBUG=False, POSTGRES_PASSWORD="db-secret",
        MIDRA_ENGINEERING_ADMIN_EMAIL="engineering@example.com",
        MIDRA_ENGINEERING_ADMIN_PASSWORD="engineering-admin-password",
        MIDRA_PROPERTY_ADMIN_EMAIL="property@example.com",
        MIDRA_PROPERTY_ADMIN_PASSWORD="property-admin-password",
        MIDRA_PROPERTY_AUTH_SECRET="property-auth-secret-0123456789",
        MIDRA_ENGINEERING_WEB_ORIGIN="https://engineering.example.com",
        PROPERTY_WEB_ORIGINS=["https://property.example.com"],
        MIDRA_PROPERTY_PUBLIC_ORIGIN="https://property.example.com",
        MIDRA_PROPOSAL_RESPONSE_SECRET="proposal-response-secret-0123456789",
        MIDRA_PROPOSAL_EMAIL_HOST="smtp.example.com",
        MIDRA_PROPOSAL_EMAIL_FROM="proposals@example.com",
        MIDRA_PROPOSAL_EMAIL_USERNAME="smtp-user",
        MIDRA_PROPOSAL_EMAIL_PASSWORD="smtp-password",
        MIDRA_PROPOSAL_EMAIL_USE_TLS=True,
        MIDRA_PROPOSAL_EMAIL_USE_SSL=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_production_ready_when_all_required_configuration_is_safe():
    result = build_production_configuration_readiness(cfg())
    assert result["status"] == "READY"
    assert result["production_ready"] is True
    assert result["client_proposal_delivery_ready"] is True
    assert result["redacted"] is True
    assert all(item["ready"] for item in result["checks"])


def test_local_or_missing_delivery_configuration_fails_closed_without_secret_leakage():
    secret="DO-NOT-LEAK-THIS-SECRET"
    result = build_production_configuration_readiness(cfg(
        APP_ENV="development", DEBUG=True,
        MIDRA_PROPERTY_PUBLIC_ORIGIN="http://localhost:4322",
        MIDRA_PROPOSAL_RESPONSE_SECRET=secret,
        MIDRA_PROPOSAL_EMAIL_HOST=None,
    ))
    assert result["production_ready"] is False
    assert result["client_proposal_delivery_ready"] is False
    rendered=str(result)
    assert secret not in rendered
    assert "smtp.example.com" not in rendered
    assert "engineering@example.com" not in rendered


def test_smtp_modes_must_be_fail_closed_and_mutually_exclusive():
    both = build_production_configuration_readiness(cfg(
        MIDRA_PROPOSAL_EMAIL_USE_TLS=True,
        MIDRA_PROPOSAL_EMAIL_USE_SSL=True,
    ))
    neither = build_production_configuration_readiness(cfg(
        MIDRA_PROPOSAL_EMAIL_USE_TLS=False,
        MIDRA_PROPOSAL_EMAIL_USE_SSL=False,
    ))
    by_name=lambda result,name: next(x for x in result["checks"] if x["name"]==name)
    assert by_name(both,"proposal_email_transport")["ready"] is False
    assert by_name(neither,"proposal_email_transport")["ready"] is False
