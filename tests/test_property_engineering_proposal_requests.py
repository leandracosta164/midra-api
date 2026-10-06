from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.repositories.property_engineering_proposal_request import SQLAlchemyPropertyEngineeringProposalRequestRepository
from datetime import datetime, timezone

def db():
    e=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(e)
    return sessionmaker(bind=e)()

def property_record(s):
    r=PropertyRecord(property_record_id="p1",canonical_key="x",search_query="1 Main St",display_address="1 Main St",municipality="Howell",county="Monmouth",block="1",lot="2",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc))
    s.add(r);s.commit();return r

def test_explicit_proposal_request_is_durable_handoff_not_job_creation():
    s=db();property_record(s)
    repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(s)
    x=repo.create(property_record_id="p1",analysis_run_id=None,project_goal="new house",customer_name="Jane",customer_email="jane@example.com")
    assert x.request_status=="REQUESTED"
    assert x.source_product=="MIDRA_PROPERTY"
    assert x.destination_product=="MIDRA_ENGINEERING"
    assert not hasattr(x,"engineering_job_number")
    assert repo.list("p1")[0].proposal_request_id==x.proposal_request_id

def test_analysis_reference_must_belong_to_property():
    s=db();property_record(s); repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(s)
    try: repo.create(property_record_id="p1",analysis_run_id="missing",project_goal="pool",customer_name="Jane",customer_email="jane@example.com")
    except KeyError as exc: assert exc.args[0]=="analysis"
    else: raise AssertionError("expected analysis ownership check")
