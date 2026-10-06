from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository


def session():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add(db, record_id, municipality, block, lot, minute):
    item=PropertyRecord(
        property_record_id=record_id,
        canonical_key=f"k-{record_id}",
        search_query=f"{record_id} address",
        display_address=f"{record_id} address",
        municipality=municipality,
        county="Monmouth",
        block=block,
        lot=lot,
        latitude=None,
        longitude=None,
        intelligence_status="MIDRA_ANALYSIS",
        latest_analysis={},
        created_at=datetime(2026,1,1,12,minute,tzinfo=timezone.utc),
        updated_at=datetime(2026,1,1,12,minute,tzinfo=timezone.utc),
    )
    db.add(item); db.commit()


def test_municipality_qualified_parcel_query_resolves_duplicate_block_lot():
    db=session()
    add(db,"howell","Howell","145","22",1)
    add(db,"freehold","Freehold","145","22",2)
    rows=SQLAlchemyPropertyRecordRepository(db).search(
        query="Howell Block 145 Lot 22",
        limit=10,
    )
    assert [r.property_record_id for r in rows]==["howell"]


def test_municipality_qualified_parcel_query_accepts_comma():
    db=session()
    add(db,"howell","Howell","145","22",1)
    rows=SQLAlchemyPropertyRecordRepository(db).search(
        query="Howell, Block 145, Lot 22",
        limit=10,
    )
    assert [r.property_record_id for r in rows]==["howell"]


def test_unqualified_parcel_query_preserves_all_matching_durable_records():
    db=session()
    add(db,"howell","Howell","145","22",1)
    add(db,"freehold","Freehold","145","22",2)
    rows=SQLAlchemyPropertyRecordRepository(db).search(query="145/22",limit=10)
    assert {r.property_record_id for r in rows}=={"howell","freehold"}
