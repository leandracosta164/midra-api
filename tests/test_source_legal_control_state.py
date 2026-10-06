from types import SimpleNamespace

from app.services.source_legal_control_state import (
    clear_legal_control,
    legal_control_promotion_decision,
)


def test_promotion_requires_strict_bound_target():
    result = legal_control_promotion_decision(
        binding={"status": "LEGAL_CONTROL_TARGET_NOT_BOUND", "legal_control_confirmed": False},
        authoritative=True,
        target_content_hash="a" * 64,
        legal_content_hash="b" * 64,
    )
    assert result == {"promotable": False, "reason": "STRICT_TARGET_BINDING_REQUIRED"}


def test_promotion_requires_independent_authority_confirmation():
    result = legal_control_promotion_decision(
        binding={"status": "LEGAL_CONTROL_TARGET_BOUND", "legal_control_confirmed": True},
        authoritative=False,
        target_content_hash="a" * 64,
        legal_content_hash="b" * 64,
    )
    assert result["promotable"] is False
    assert result["reason"] == "SOURCE_AUTHORITY_NOT_CONFIRMED"


def test_promotion_requires_version_fingerprints():
    result = legal_control_promotion_decision(
        binding={"status": "LEGAL_CONTROL_TARGET_BOUND", "legal_control_confirmed": True},
        authoritative=True,
        target_content_hash=None,
        legal_content_hash="b" * 64,
    )
    assert result["promotable"] is False
    assert result["reason"] == "VERSION_FINGERPRINT_REQUIRED"


def test_promotion_accepts_bound_authoritative_versioned_source():
    result = legal_control_promotion_decision(
        binding={"status": "LEGAL_CONTROL_TARGET_BOUND", "legal_control_confirmed": True},
        authoritative=True,
        target_content_hash="a" * 64,
        legal_content_hash="b" * 64,
    )
    assert result == {"promotable": True, "reason": "EXPLICIT_LEGAL_CONTROL_VERIFIED"}


def test_clear_legal_control_removes_all_verification_state():
    row = SimpleNamespace(
        legal_control_confirmed=True,
        legal_control_verified_at=object(),
        legal_control_target_hash="a" * 64,
        legal_control_evidence_url="https://example.gov/code",
        legal_control_evidence_hash="b" * 64,
        legal_control_matched_reference="https://example.gov/map",
    )
    clear_legal_control(row)
    assert row.legal_control_confirmed is False
    assert row.legal_control_verified_at is None
    assert row.legal_control_target_hash is None
    assert row.legal_control_evidence_url is None
    assert row.legal_control_evidence_hash is None
    assert row.legal_control_matched_reference is None
