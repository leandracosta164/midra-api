from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.repositories.property_record import SQLAlchemyPropertyRecordRepository


def _analysis(address="123 Main St, Howell, NJ"):
    return {
        "mode": "preliminary",
        "property": {
            "address": address,
            "municipality": "Howell Township",
            "county": "Monmouth",
            "parcel": {"block": "12", "lot": "3"},
            "coordinates": {"latitude": 40.1, "longitude": -74.2},
        },
        "verification_items": ["VERIFY wetlands"],
    }


def _repo():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[PropertyRecord.__table__])
    db = sessionmaker(bind=engine)()
    return SQLAlchemyPropertyRecordRepository(db)


def test_property_record_is_durable_and_property_owned():
    r = _repo()
    record = r.upsert_from_analysis(search_query="123 Main St", analysis=_analysis())
    assert record.property_record_id
    assert record.canonical_key == "nj-parcel|howell township|12|3"
    assert record.intelligence_status == "MIDRA_ANALYSIS"
    assert record.latest_analysis["verification_items"] == ["VERIFY wetlands"]
    assert not hasattr(record, "engineering_job_number")
    loaded = r.get(record.property_record_id)
    assert loaded.display_address == "123 Main St, Howell, NJ"


def test_same_parcel_updates_instead_of_creating_duplicate_property():
    r = _repo()
    first = r.upsert_from_analysis(search_query="123 Main St", analysis=_analysis())
    second_analysis = _analysis("123 Main Street, Howell, NJ")
    second_analysis["summary"] = "updated"
    second = r.upsert_from_analysis(search_query="123 Main Street", analysis=second_analysis)
    assert second.property_record_id == first.property_record_id
    assert second.latest_analysis["summary"] == "updated"


def test_property_record_router_is_registered_without_replacing_intelligence_api():
    from app.main import app
    paths = {route.path for route in app.routes}
    assert "/property-records" in paths
    assert "/property-records/{property_record_id}" in paths
    assert "/property-intelligence/analyze" in paths
    assert "/property-intelligence/suggest" in paths
