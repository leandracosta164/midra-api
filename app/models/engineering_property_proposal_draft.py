"""Durable MIDRA Engineering proposal drafts created from Property proposal intake."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalDraft(Base):
    __tablename__ = "engineering_property_proposal_drafts"

    engineering_draft_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    property_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_records.property_record_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "property_engineering_proposal_requests.proposal_request_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    proposal_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="DRAFT_REQUIRES_ENGINEER_REVIEW", index=True
    )
    draft_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
