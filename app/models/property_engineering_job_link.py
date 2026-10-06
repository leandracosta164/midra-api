"""Durable Property-owned reference to an existing MIDRA Engineering job."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PropertyEngineeringJobLink(Base):
    __tablename__ = "property_engineering_job_links"
    __table_args__ = (UniqueConstraint("property_record_id", "engineering_job_number", name="uq_property_engineering_job_link"),)

    link_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    property_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_records.property_record_id", ondelete="CASCADE"), nullable=False, index=True
    )
    engineering_job_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    link_status: Mapped[str] = mapped_column(String(20), nullable=False, default="linked", index=True)
    created_by: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
