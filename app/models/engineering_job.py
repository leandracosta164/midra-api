"""MIDRA Engineering Job ORM model — native SQLAlchemy/PostgreSQL architecture."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EngineeringJob(Base):
    __tablename__ = "engineering_jobs"

    job_number: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_name: Mapped[str] = mapped_column(String(300), nullable=False)
    project_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    property_address: Mapped[str | None] = mapped_column(String(500))
    client_id: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
