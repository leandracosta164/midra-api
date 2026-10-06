from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.engineering_job import EngineeringJob
from app.models.property_record import PropertyRecord
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository
from app.repositories.property_engineering_job_link import SQLAlchemyPropertyEngineeringJobLinkRepository


def _db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine,tables=[EngineeringJob.__table__,PropertyRecord.__table__,PropertyEngineeringJobLink.__table__])
    return sessionmaker(bind=engine)()


def _property(db):
    return SQLAlchemyPropertyRecordRepository(db).upsert_from_analysis(search_query="123 Main St",analysis={"property":{"address":"123 Main St, Howell, NJ","municipality":"Howell Township","parcel":{"block":"12","lot":"3"}}})


def test_property_can_link_multiple_existing_engineering_jobs_without_owning_them():
    db=_db(); record=_property(db)
    for n in ("26-0101","26-0102"):
        db.add(EngineeringJob(job_number=n,project_name=n,project_type="civil",source="test",sections={},events=[]))
    db.commit(); links=SQLAlchemyPropertyEngineeringJobLinkRepository(db)
    links.link(property_record_id=record.property_record_id,engineering_job_number="26-0101")
    links.link(property_record_id=record.property_record_id,engineering_job_number="26-0102")
    assert {x.engineering_job_number for x in links.list(record.property_record_id)}=={"26-0101","26-0102"}
    assert not hasattr(record,"engineering_job_number")
    assert not hasattr(PropertyEngineeringJobLink,"engineer_accepted")


def test_link_requires_existing_engineering_job_and_unlink_preserves_boundary():
    db=_db(); record=_property(db); links=SQLAlchemyPropertyEngineeringJobLinkRepository(db)
    try: links.link(property_record_id=record.property_record_id,engineering_job_number="99-9999")
    except KeyError as exc: assert exc.args[0]=="engineering_job"
    else: raise AssertionError("missing Engineering job must not be linked")
    db.add(EngineeringJob(job_number="26-0103",project_name="test",project_type="civil",source="test",sections={},events=[]));db.commit()
    links.link(property_record_id=record.property_record_id,engineering_job_number="26-0103")
    links.unlink(property_record_id=record.property_record_id,engineering_job_number="26-0103")
    assert links.list(record.property_record_id)==[]
