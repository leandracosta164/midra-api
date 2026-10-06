from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.repositories.property_analysis_run import SQLAlchemyPropertyAnalysisRunRepository


def session():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def property_record(db, record_id):
    item=PropertyRecord(
        property_record_id=record_id,
        canonical_key=f"k-{record_id}",
        search_query=f"{record_id} address",
        display_address=f"{record_id} address",
        municipality="Howell",
        county="Monmouth",
        block="1",
        lot="2",
        latitude=None,
        longitude=None,
        intelligence_status="MIDRA_ANALYSIS",
        latest_analysis={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(item); db.commit()


def test_exact_analysis_run_resolves_only_for_owning_property():
    db=session()
    property_record(db,"p1")
    property_record(db,"p2")
    repo=SQLAlchemyPropertyAnalysisRunRepository(db)
    run=repo.append(property_record_id="p1",analysis={"project_goal":"pool"})
    assert repo.get("p1",run.analysis_run_id).analysis_run_id==run.analysis_run_id
    try:
        repo.get("p2",run.analysis_run_id)
    except KeyError as exc:
        assert exc.args[0]=="analysis_run"
    else:
        raise AssertionError("analysis run must not resolve across Property records")


def test_exact_analysis_run_rejects_unknown_id():
    db=session()
    property_record(db,"p1")
    repo=SQLAlchemyPropertyAnalysisRunRepository(db)
    try:
        repo.get("p1","missing")
    except KeyError as exc:
        assert exc.args[0]=="analysis_run"
    else:
        raise AssertionError("unknown analysis run must be rejected")
