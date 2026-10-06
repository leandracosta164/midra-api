from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.engineering_job import EngineeringJob
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_record import PropertyRecord


class SQLAlchemyPropertyEngineeringJobLinkRepository:
    def __init__(self, db: Session):
        self.db = db

    def _property(self, property_record_id: str) -> PropertyRecord:
        record = self.db.get(PropertyRecord, property_record_id)
        if record is None:
            raise KeyError("property")
        return record

    def _job(self, job_number: str) -> EngineeringJob:
        job = self.db.get(EngineeringJob, job_number)
        if job is None:
            raise KeyError("engineering_job")
        return job

    def list(self, property_record_id: str, *, include_unlinked: bool = False) -> list[PropertyEngineeringJobLink]:
        self._property(property_record_id)
        stmt = select(PropertyEngineeringJobLink).where(PropertyEngineeringJobLink.property_record_id == property_record_id)
        if not include_unlinked:
            stmt = stmt.where(PropertyEngineeringJobLink.link_status == "linked")
        stmt = stmt.order_by(PropertyEngineeringJobLink.created_at.desc())
        return list(self.db.scalars(stmt))

    def link(self, *, property_record_id: str, engineering_job_number: str, created_by: str | None = None, notes: str | None = None) -> PropertyEngineeringJobLink:
        job_number = engineering_job_number.strip()
        self._property(property_record_id)
        self._job(job_number)
        existing = self.db.scalar(select(PropertyEngineeringJobLink).where(
            PropertyEngineeringJobLink.property_record_id == property_record_id,
            PropertyEngineeringJobLink.engineering_job_number == job_number,
        ))
        now = datetime.now(timezone.utc)
        if existing is None:
            existing = PropertyEngineeringJobLink(
                link_id=str(uuid.uuid4()), property_record_id=property_record_id,
                engineering_job_number=job_number, link_status="linked",
                created_by=(created_by or "").strip() or None, notes=(notes or "").strip() or None,
                created_at=now, updated_at=now,
            )
            self.db.add(existing)
        else:
            existing.link_status = "linked"
            existing.created_by = (created_by or "").strip() or existing.created_by
            existing.notes = (notes or "").strip() or None
            existing.updated_at = now
        self.db.commit(); self.db.refresh(existing)
        return existing

    def unlink(self, *, property_record_id: str, engineering_job_number: str) -> PropertyEngineeringJobLink:
        self._property(property_record_id)
        existing = self.db.scalar(select(PropertyEngineeringJobLink).where(
            PropertyEngineeringJobLink.property_record_id == property_record_id,
            PropertyEngineeringJobLink.engineering_job_number == engineering_job_number.strip(),
        ))
        if existing is None or existing.link_status != "linked":
            raise KeyError("link")
        existing.link_status = "unlinked"
        existing.updated_at = datetime.now(timezone.utc)
        self.db.commit(); self.db.refresh(existing)
        return existing
