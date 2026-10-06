from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository

def test_recent_property_workspace_uses_durable_records_and_orders_activity():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=sessionmaker(bind=engine)()
    now=datetime.now(timezone.utc)
    older=PropertyRecord(property_record_id="old",canonical_key="old",search_query="1 Old St",display_address="1 Old St",municipality="Howell",county="Monmouth",block="1",lot="1",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=now-timedelta(days=2),updated_at=now-timedelta(days=2))
    newer=PropertyRecord(property_record_id="new",canonical_key="new",search_query="2 New St",display_address="2 New St",municipality="Marlboro",county="Monmouth",block="2",lot="2",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=now-timedelta(days=1),updated_at=now)
    db.add_all([older,newer]);db.commit()
    rows=SQLAlchemyPropertyRecordRepository(db).list_recent(limit=25)
    assert [x.property_record_id for x in rows]==["new","old"]

def test_recent_property_workspace_limit_is_bounded():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=sessionmaker(bind=engine)()
    assert SQLAlchemyPropertyRecordRepository(db).list_recent(limit=10000)==[]
