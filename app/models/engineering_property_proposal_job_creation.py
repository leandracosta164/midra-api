"""Durable audit record for authorized Engineering job creation from an accepted Property proposal."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringPropertyProposalJobCreation(Base):
    __tablename__ = "engineering_property_proposal_job_creations"
    __table_args__ = (
        UniqueConstraint("engineering_client_response_id", name="uq_epp_job_create_response"),
        UniqueConstraint("proposal_request_id", name="uq_epp_job_create_request"),
        UniqueConstraint("engineering_job_number", name="uq_epp_job_create_job"),
        Index("ix_epp_job_create_property", "property_record_id"),
        Index("ix_epp_job_create_request", "proposal_request_id"),
        Index("ix_epp_job_create_response", "engineering_client_response_id"),
        Index("ix_epp_job_create_job", "engineering_job_number"),
    )

    engineering_job_creation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engineering_client_response_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "engineering_property_proposal_client_responses.engineering_client_response_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    property_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_records.property_record_id", ondelete="CASCADE"), nullable=False
    )
    proposal_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("property_engineering_proposal_requests.proposal_request_id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_id: Mapped[str] = mapped_column(String(40), nullable=False)
    proposal_number: Mapped[str] = mapped_column(String(100), nullable=False)
    engineering_job_number: Mapped[str] = mapped_column(
        String(50), ForeignKey("engineering_jobs.job_number", ondelete="RESTRICT"), nullable=False
    )
    creation_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
