"""Durable transport audit records for Property-origin Engineering proposal delivery."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalDelivery(Base):
    __tablename__ = "engineering_property_proposal_deliveries"

    engineering_delivery_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineering_release_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("engineering_property_proposal_releases.engineering_release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("engineering_property_proposal_pdf_artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_records.property_record_id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposal_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_engineering_proposal_requests.proposal_request_id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    authorized_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
