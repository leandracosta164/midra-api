from hashlib import sha256
from types import SimpleNamespace

import pytest

from app.services.engineering_proposal_delivery import InMemoryProposalDeliveryTransport
from app.services.engineering_property_proposal_delivery_bridge import deliver_durable_property_proposal_pdf
from app.services.engineering_proposal_email_transport import SMTPProposalDeliveryTransport


PDF=b"%PDF-1.4\nMIDRA\n"
HASH=sha256(PDF).hexdigest()


class FakeArtifactRepo:
    def __init__(self):
        self.item=SimpleNamespace(
            artifact_id="MEPDF-ABC",
            engineering_release_id="db-release-1",
            proposal_number="P-2026-1",
            filename="MIDRA_Engineering_Proposal_P-2026-1.pdf",
            mime_type="application/pdf",
            pdf_sha256=HASH,
            byte_size=len(PDF),
            pdf_bytes=PDF,
            artifact_snapshot={"release_id":"MER-CLIENTSAFE"},
        )
    def get(self, artifact_id):
        return self.item if artifact_id==self.item.artifact_id else None
    @staticmethod
    def exact_bytes(item):
        return bytes(item.pdf_bytes)


def test_durable_bridge_sends_exact_stored_bytes_without_rerender():
    repo=FakeArtifactRepo()
    transport=InMemoryProposalDeliveryTransport()
    result=deliver_durable_property_proposal_pdf(
        artifact=repo.item,
        recipient="Client@Example.com",
        authorized_by="engineer@example.com",
        explicit_send_authorized=True,
        artifact_repo=repo,
        transport=transport,
    )
    assert result["status"]=="SENT"
    assert result["artifact_id"]=="MEPDF-ABC"
    assert result["release_id"]=="MER-CLIENTSAFE"
    assert result["pdf_sha256"]==HASH
    assert result["recipient"]=="client@example.com"
    assert result["automatic_send"] is False
    assert transport.deliveries[0]["content"]==PDF


def test_durable_bridge_refuses_automatic_or_implicit_send():
    repo=FakeArtifactRepo()
    with pytest.raises(PermissionError, match="explicit authorized send"):
        deliver_durable_property_proposal_pdf(
            artifact=repo.item,
            recipient="client@example.com",
            authorized_by="engineer@example.com",
            explicit_send_authorized=False,
            artifact_repo=repo,
            transport=InMemoryProposalDeliveryTransport(),
        )


def test_smtp_transport_is_fail_closed_until_configured():
    with pytest.raises(ValueError, match="not configured"):
        SMTPProposalDeliveryTransport(host="", port=587, from_email="")
