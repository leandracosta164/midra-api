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


def add(db, record_id, address, block, lot, minute):
    item=PropertyRecord(
        property_record_id=record_id,
        canonical_key=f"k-{record_id}",
        search_query=address,
        display_address=address,
        municipality="Howell",
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


def test_labeled_block_lot_query_requires_combined_identity():
    db=session()
    add(db,"wrong-block","1 A Street","145","99",1)
    add(db,"wrong-lot","2 B Street","999","22",2)
    add(db,"target","3 C Street","145","22",0)
    rows=SQLAlchemyPropertyRecordRepository(db).search(query="Block 145 Lot 22",limit=10)
    assert [r.property_record_id for r in rows]==["target"]


def test_compact_block_lot_query_reopens_exact_durable_parcel():
    db=session()
    add(db,"target","3 C Street","145.01","22.02",0)
    rows=SQLAlchemyPropertyRecordRepository(db).search(query="145.01/22.02",limit=10)
    assert [r.property_record_id for r in rows]==["target"]


def test_plain_address_search_remains_supported():
    db=session()
    add(db,"target","77 Hidden Lane","145","22",0)
    rows=SQLAlchemyPropertyRecordRepository(db).search(query="Hidden",limit=10)
    assert [r.property_record_id for r in rows]==["target"]
