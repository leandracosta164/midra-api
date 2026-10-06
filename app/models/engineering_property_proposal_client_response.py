"""Durable client responses for released Property-origin Engineering proposals."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalClientResponse(Base):
    __tablename__ = "engineering_property_proposal_client_responses"
    __table_args__ = (
        UniqueConstraint(
            "engineering_release_id",
            name="uq_engineering_property_proposal_client_response_release",
        ),
        Index("ix_epp_client_resp_release", "engineering_release_id"),
        Index("ix_epp_client_resp_property", "property_record_id"),
        Index("ix_epp_client_resp_request", "proposal_request_id"),
        Index("ix_epp_client_resp_proposal", "proposal_id"),
        Index("ix_epp_client_resp_number", "proposal_number"),
        Index("ix_epp_client_resp_status", "response_status"),
    )

    engineering_client_response_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineering_release_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "engineering_property_proposal_releases.engineering_release_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    property_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_records.property_record_id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "property_engineering_proposal_requests.proposal_request_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False)
    response_status: Mapped[str] = mapped_column(String(30), nullable=False)
    response_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
