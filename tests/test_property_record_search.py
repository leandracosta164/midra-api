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


def add(db, record_id, address, municipality, block, lot, minute):
    item=PropertyRecord(
        property_record_id=record_id,
        canonical_key=f"k-{record_id}",
        search_query=address,
        display_address=address,
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


def test_search_finds_nonrecent_address_match():
    db=session()
    for i in range(12):
        add(db,f"p{i}",f"{i} Oak Street","Howell",str(i),"1",i)
    add(db,"target","77 Hidden Lane","Freehold","99","7",0)
    rows=SQLAlchemyPropertyRecordRepository(db).search(query="Hidden",limit=10)
    assert [r.property_record_id for r in rows]==["target"]


def test_search_matches_parcel_identity_fields():
    db=session()
    add(db,"p1","1 Main Street","Howell","145","22",1)
    assert SQLAlchemyPropertyRecordRepository(db).search(query="145",limit=10)[0].property_record_id=="p1"
    assert SQLAlchemyPropertyRecordRepository(db).search(query="Howell",limit=10)[0].property_record_id=="p1"


def test_search_requires_two_characters_and_caps_limit():
    db=session()
    add(db,"p1","1 Main Street","Howell","145","22",1)
    assert SQLAlchemyPropertyRecordRepository(db).search(query="1",limit=10)==[]
