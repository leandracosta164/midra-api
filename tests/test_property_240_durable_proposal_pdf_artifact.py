from hashlib import sha256

from app.models.engineering_property_proposal_pdf_artifact import EngineeringPropertyProposalPdfArtifact
from app.repositories.engineering_property_proposal_pdf_artifact import SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository
from app.services.engineering_proposal_release import create_proposal_release_snapshot
from app.services.engineering_proposal_pdf_artifact import build_proposal_pdf_artifact_manifest
from app.services.engineering_proposal_pdf_renderer import render_proposal_pdf
from app.services.engineering_proposal_pdf_repository import InMemoryProposalPdfStore, persist_rendered_proposal_pdf, retrieve_proposal_pdf


def approved_proposal():
    return {
        "status": "APPROVED_READY_TO_SEND",
        "proposal_number": "P-240-001",
        "proposal_date": "2026-10-04",
        "project": {"name": "Test Project", "address": "1 Main St, Howell, NJ"},
        "prepared_for": {"name": "Test Client"},
        "services": [{"name": "Site Engineering", "proposal_price": 1500.0}],
        "total_price": 1500.0,
        "exclusions_additional_services": ["Survey by others"],
        "terms": ["Payment due per executed agreement"],
    }


def test_exact_pdf_bytes_survive_artifact_contract_without_rerender():
    release = create_proposal_release_snapshot(proposal=approved_proposal(), released_by="engineer@example.com")
    manifest = build_proposal_pdf_artifact_manifest(release=release)
    rendered = render_proposal_pdf(artifact=manifest)
    store = InMemoryProposalPdfStore()
    persisted = persist_rendered_proposal_pdf(rendered=rendered, store=store)
    retrieved = retrieve_proposal_pdf(artifact_id=persisted["artifact_id"], store=store)
    assert retrieved["pdf_bytes"] == rendered["pdf_bytes"]
    assert sha256(retrieved["pdf_bytes"]).hexdigest() == retrieved["pdf_sha256"]
    assert retrieved["immutable"] is True
    assert retrieved["transport"]["sent"] is False


def test_durable_model_keeps_bytes_private_from_snapshot_and_integrity_helper():
    data = b"%PDF-1.4\nMIDRA\n"
    digest = sha256(data).hexdigest()
    item = EngineeringPropertyProposalPdfArtifact(
        artifact_id="MEPDF-TEST",
        engineering_release_id="release-1",
        property_record_id="property-1",
        proposal_request_id="request-1",
        proposal_id="proposal-1",
        proposal_number="P-1",
        filename="proposal.pdf",
        mime_type="application/pdf",
        pdf_sha256=digest,
        byte_size=len(data),
        pdf_bytes=data,
        artifact_snapshot={"artifact_id": "MEPDF-TEST", "immutable": True},
        created_by="engineer@example.com",
    )
    assert "pdf_bytes" not in item.artifact_snapshot
    assert SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository.exact_bytes(item) == data
    item.pdf_bytes = b"tampered"
    try:
        SQLAlchemyEngineeringPropertyProposalPdfArtifactRepository.exact_bytes(item)
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("tampered durable bytes must fail closed")
