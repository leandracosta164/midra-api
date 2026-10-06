from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceCatalog(Base):
    """Current catalog/provenance metadata for discovered public sources."""

    __tablename__ = "midra_source_catalog"
    __table_args__ = (
        UniqueConstraint("municipality", "source_url", name="uq_midra_source_catalog_municipality_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    municipality: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    retrieval_url: Mapped[str | None] = mapped_column(String(2048), index=True)
    source_role: Mapped[str] = mapped_column(String(100), nullable=False)
    authority_tier: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(100), nullable=False)
    discovery_source: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str | None] = mapped_column(String(100))
    authoritative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    legal_control_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    legal_control_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    legal_control_target_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    legal_control_evidence_url: Mapped[str | None] = mapped_column(String(2048))
    legal_control_evidence_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    legal_control_matched_reference: Mapped[str | None] = mapped_column(String(2048))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    current_status: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
