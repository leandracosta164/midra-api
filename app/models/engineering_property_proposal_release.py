"""Durable client-release records for approved Property-origin Engineering proposals."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalRelease(Base):
    __tablename__ = "engineering_property_proposal_releases"
    __table_args__ = (
        UniqueConstraint("engineering_review_id", name="uq_engineering_property_proposal_release_review"),
    )

    engineering_release_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineering_review_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("engineering_property_proposal_reviews.engineering_review_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_records.property_record_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_engineering_proposal_requests.proposal_request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    release_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    released_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    released_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
