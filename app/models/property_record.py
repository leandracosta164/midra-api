"""Durable MIDRA Property record owned by the Property product."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PropertyRecord(Base):
    __tablename__ = "property_records"

    property_record_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(700), nullable=False, unique=True, index=True)
    search_query: Mapped[str] = mapped_column(String(500), nullable=False)
    display_address: Mapped[str] = mapped_column(String(500), nullable=False)
    municipality: Mapped[str | None] = mapped_column(String(200), index=True)
    county: Mapped[str | None] = mapped_column(String(200))
    block: Mapped[str | None] = mapped_column(String(100), index=True)
    lot: Mapped[str | None] = mapped_column(String(100), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    intelligence_status: Mapped[str] = mapped_column(String(50), nullable=False, default="MIDRA_ANALYSIS")
    latest_analysis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
