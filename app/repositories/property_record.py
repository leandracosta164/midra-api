from datetime import datetime, timezone
import hashlib
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.property_record import PropertyRecord


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", _text(value)).lower()


def _identity(analysis: dict, search_query: str) -> dict:
    prop = analysis.get("property") or {}
    parcel = prop.get("parcel") or (analysis.get("property_resolution") or {}).get("parcel") or {}
    coords = prop.get("coordinates") or (analysis.get("property_resolution") or {}).get("coordinates") or {}
    municipality = _text(prop.get("municipality")) or None
    block = _text(parcel.get("block")) or None
    lot = _text(parcel.get("lot")) or None
    display_address = _text(prop.get("address")) or search_query.strip()
    if municipality and block and lot:
        canonical = f"nj-parcel|{_norm(municipality)}|{_norm(block)}|{_norm(lot)}"
    else:
        canonical = f"nj-address|{_norm(display_address)}"
    # Bound the indexed key while retaining deterministic identity.
    if len(canonical) > 650:
        canonical = "sha256|" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "canonical_key": canonical,
        "display_address": display_address,
        "municipality": municipality,
        "county": _text(prop.get("county") or parcel.get("county")) or None,
        "block": block,
        "lot": lot,
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
    }


class SQLAlchemyPropertyRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_from_analysis(self, *, search_query: str, analysis: dict) -> PropertyRecord:
        identity = _identity(analysis, search_query)
        record = self.db.scalar(select(PropertyRecord).where(PropertyRecord.canonical_key == identity["canonical_key"]))
        now = datetime.now(timezone.utc)
        if record is None:
            record = PropertyRecord(
                property_record_id=str(uuid.uuid4()),
                search_query=search_query.strip(),
                intelligence_status="MIDRA_ANALYSIS",
                latest_analysis=analysis,
                created_at=now,
                updated_at=now,
                **identity,
            )
            self.db.add(record)
        else:
            record.search_query = search_query.strip()
            record.display_address = identity["display_address"]
            record.municipality = identity["municipality"]
            record.county = identity["county"]
            record.block = identity["block"]
            record.lot = identity["lot"]
            record.latitude = identity["latitude"]
            record.longitude = identity["longitude"]
            record.latest_analysis = analysis
            record.intelligence_status = "MIDRA_ANALYSIS"
            record.updated_at = now
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, property_record_id: str) -> PropertyRecord:
        record = self.db.get(PropertyRecord, property_record_id)
        if record is None:
            raise KeyError(property_record_id)
        return record


    def _parcel_search_parts(self, query: str) -> tuple[str | None, str, str] | None:
        """Recognize explicit durable parcel identity queries without guessing."""
        text = _text(query)
        qualified = re.fullmatch(
            r"\s*(.+?)\s*,?\s+(?:block|blk)\s*[:#]?\s*([A-Za-z0-9.\-]+)\s*(?:,|\s)+\s*(?:lot|lt)\s*[:#]?\s*([A-Za-z0-9.\-]+)\s*",
            text,
            flags=re.IGNORECASE,
        )
        if qualified:
            municipality = _text(qualified.group(1)) or None
            return (municipality, _text(qualified.group(2)), _text(qualified.group(3)))
        labeled = re.fullmatch(
            r"\s*(?:block|blk)\s*[:#]?\s*([A-Za-z0-9.\-]+)\s*(?:,|\s)+\s*(?:lot|lt)\s*[:#]?\s*([A-Za-z0-9.\-]+)\s*",
            text,
            flags=re.IGNORECASE,
        )
        if labeled:
            return (None, _text(labeled.group(1)), _text(labeled.group(2)))
        compact = re.fullmatch(
            r"\s*([A-Za-z0-9.\-]+)\s*/\s*([A-Za-z0-9.\-]+)\s*",
            text,
        )
        if compact:
            return (None, _text(compact.group(1)), _text(compact.group(2)))
        return None

    def search(self, *, query: str, limit: int = 10) -> list[PropertyRecord]:
        """Search durable Property records without limiting matches to recent history."""
        needle = _text(query)
        if len(needle) < 2:
            return []
        safe_limit = max(1, min(int(limit), 25))
        parcel = self._parcel_search_parts(needle)
        if parcel:
            municipality, block, lot = parcel
            identity_filter = (
                PropertyRecord.block.ilike(block)
                & PropertyRecord.lot.ilike(lot)
            )
            if municipality:
                identity_filter = identity_filter & PropertyRecord.municipality.ilike(municipality)
            stmt = (
                select(PropertyRecord)
                .where(identity_filter)
                .order_by(PropertyRecord.updated_at.desc(), PropertyRecord.created_at.desc())
                .limit(safe_limit)
            )
            return list(self.db.scalars(stmt))

        pattern = f"%{needle}%"
        stmt = (
            select(PropertyRecord)
            .where(
                PropertyRecord.display_address.ilike(pattern)
                | PropertyRecord.search_query.ilike(pattern)
                | PropertyRecord.municipality.ilike(pattern)
                | PropertyRecord.block.ilike(pattern)
                | PropertyRecord.lot.ilike(pattern)
            )
            .order_by(PropertyRecord.updated_at.desc(), PropertyRecord.created_at.desc())
            .limit(safe_limit)
        )
        return list(self.db.scalars(stmt))


    def list_recent(self, *, limit: int = 25) -> list[PropertyRecord]:
        """Return durable Property records by most recent Property activity."""
        safe_limit = max(1, min(int(limit), 100))
        stmt = (
            select(PropertyRecord)
            .order_by(PropertyRecord.updated_at.desc(), PropertyRecord.created_at.desc())
            .limit(safe_limit)
        )
        return list(self.db.scalars(stmt))
