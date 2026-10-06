from app.services.proposal_delivery_history import (
    record_delivery_event, proposal_delivery_history, proposal_delivery_status,
    delivery_audit_view,
)
import pytest

BASE = dict(
    proposal_id="ME-P-0001", release_id="REL-1", artifact_id="PDF-1",
    recipient="client@example.com", pdf_sha256="a"*64, authorized_by="engineer-1",
)

def test_no_delivery_history_projects_not_sent():
    assert proposal_delivery_status(proposal_id="P0", events=[])["status"] == "NOT_SENT"

def test_sent_event_preserves_exact_artifact_identity_and_hash():
    e = record_delivery_event(**BASE, status="SENT", occurred_at="2026-09-18T01:00:00+00:00")
    assert e["artifact_id"] == "PDF-1" and e["pdf_sha256"] == "a"*64

def test_history_is_scoped_to_requested_proposal():
    e1 = record_delivery_event(**BASE, status="SENT", occurred_at="2026-09-18T01:00:00+00:00")
    other = dict(BASE); other["proposal_id"] = "ME-P-0002"
    e2 = record_delivery_event(**other, status="SENT", occurred_at="2026-09-18T01:01:00+00:00")
    assert proposal_delivery_history(proposal_id="ME-P-0001", events=[e1,e2]) == [e1]

def test_history_is_chronological_and_append_only_projection():
    later = record_delivery_event(**BASE, status="DELIVERED", occurred_at="2026-09-18T02:00:00+00:00")
    earlier = record_delivery_event(**BASE, status="SENT", occurred_at="2026-09-18T01:00:00+00:00")
    history = proposal_delivery_history(proposal_id="ME-P-0001", events=[later, earlier])
    assert [x["status"] for x in history] == ["SENT", "DELIVERED"]

def test_latest_event_drives_current_delivery_status():
    sent = record_delivery_event(**BASE, status="SENT", occurred_at="2026-09-18T01:00:00+00:00")
    delivered = record_delivery_event(**BASE, status="DELIVERED", delivery_id="D-1",
                                      occurred_at="2026-09-18T02:00:00+00:00")
    result = proposal_delivery_status(proposal_id="ME-P-0001", events=[sent, delivered])
    assert result["status"] == "DELIVERED" and result["latest_event"]["delivery_id"] == "D-1"

def test_failed_delivery_is_visible_not_erased():
    failed = record_delivery_event(**BASE, status="FAILED", occurred_at="2026-09-18T03:00:00+00:00")
    assert proposal_delivery_status(proposal_id="ME-P-0001", events=[failed])["status"] == "FAILED"

def test_invalid_status_cannot_be_written_to_history():
    with pytest.raises(ValueError):
        record_delivery_event(**BASE, status="APPROVED_READY_TO_SEND")

def test_private_engineering_audit_view_preserves_authorization_and_recipient():
    e = record_delivery_event(**BASE, status="SENT", delivery_id="D-9",
                              occurred_at="2026-09-18T01:00:00+00:00")
    audit = delivery_audit_view(event=e)
    assert audit["recipient"] == "client@example.com"
    assert audit["authorized_by"] == "engineer-1"
    assert audit["delivery_id"] == "D-9"
