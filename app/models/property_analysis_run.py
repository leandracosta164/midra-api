"""Immutable analysis history for a durable MIDRA Property record."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PropertyAnalysisRun(Base):
    __tablename__ = "property_analysis_runs"

    analysis_run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    property_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("property_records.property_record_id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_work: Mapped[str | None] = mapped_column(String(500))
    intelligence_status: Mapped[str] = mapped_column(String(50), nullable=False, default="MIDRA_ANALYSIS")
    analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
