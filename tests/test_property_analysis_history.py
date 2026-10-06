from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository
from app.repositories.property_analysis_run import SQLAlchemyPropertyAnalysisRunRepository

def analysis(summary):
    return {"property":{"address":"123 Main St, Howell, NJ","municipality":"Howell Township","parcel":{"block":"12","lot":"3"}},"summary":summary,"verification_items":["VERIFY"]}

def test_durable_history_preserves_each_midra_analysis():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine,tables=[PropertyRecord.__table__,PropertyAnalysisRun.__table__])
    db=sessionmaker(bind=engine)(); records=SQLAlchemyPropertyRecordRepository(db); history=SQLAlchemyPropertyAnalysisRunRepository(db)
    record=records.upsert_from_analysis(search_query="123 Main St",analysis=analysis("first")); history.append(property_record_id=record.property_record_id,analysis=analysis("first"))
    record=records.upsert_from_analysis(search_query="123 Main Street",analysis=analysis("second")); history.append(property_record_id=record.property_record_id,analysis=analysis("second"))
    runs=history.list(record.property_record_id)
    assert len(runs)==2
    assert {r.analysis["summary"] for r in runs}=={"first","second"}
    assert record.latest_analysis["summary"]=="second"
    assert all(r.intelligence_status=="MIDRA_ANALYSIS" for r in runs)

def test_history_does_not_claim_engineer_acceptance():
    assert not hasattr(PropertyAnalysisRun,"engineering_job_number")
    assert not hasattr(PropertyAnalysisRun,"engineer_accepted")
