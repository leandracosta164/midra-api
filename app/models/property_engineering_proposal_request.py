"""Durable outbound MIDRA Property -> MIDRA Engineering proposal request."""
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class PropertyEngineeringProposalRequest(Base):
    __tablename__ = "property_engineering_proposal_requests"
    proposal_request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    property_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_records.property_record_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    analysis_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    project_goal: Mapped[str] = mapped_column(Text, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(80))
    request_status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED", index=True)
    source_product: Mapped[str] = mapped_column(String(40), nullable=False, default="MIDRA_PROPERTY")
    destination_product: Mapped[str] = mapped_column(String(40), nullable=False, default="MIDRA_ENGINEERING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
