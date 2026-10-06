"""Durable immutable PDF artifact for one Property-origin Engineering proposal release."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalPdfArtifact(Base):
    __tablename__ = "engineering_property_proposal_pdf_artifacts"
    __table_args__ = (
        UniqueConstraint("engineering_release_id", name="uq_engineering_property_proposal_pdf_release"),
    )

    artifact_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    engineering_release_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("engineering_property_proposal_releases.engineering_release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_record_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    proposal_request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    artifact_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
