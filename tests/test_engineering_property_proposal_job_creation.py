from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.engineering_job import EngineeringJob
from app.models.engineering_property_proposal_client_response import EngineeringPropertyProposalClientResponse
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.engineering_property_proposal_job_creation import EngineeringPropertyProposalJobCreation
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.property_record import PropertyRecord
from app.repositories.engineering_property_proposal_job_creation import SQLAlchemyEngineeringPropertyProposalJobCreationRepository
from app.services.property_engineering_job_creation_bridge import build_authorized_engineering_job_creation


def _service_inputs(status="CLIENT_APPROVED",response="ACCEPTED"):
    record=SimpleNamespace(property_record_id="p1",display_address="1 Main St",search_query="1 Main St",municipality="Howell",county="Monmouth",block="1",lot="2")
    proposal=SimpleNamespace(proposal_request_id="r1",analysis_run_id="a1",request_status=status,project_goal="pool",customer_name="Jane",customer_email="jane@example.com",customer_phone=None)
    client=SimpleNamespace(engineering_client_response_id="c1",proposal_id="MEP-1",proposal_number="P-1",response_status=response,response_snapshot={"client_response_status":response,"client_approved":response=="ACCEPTED","engineering_job_created":False,"project":"Pool Engineering"})
    return record,proposal,client


def test_bridge_requires_client_approved_and_accepted_response():
    record,proposal,client=_service_inputs()
    built=build_authorized_engineering_job_creation(property_record=record,proposal_request=proposal,client_response=client,engineering_user="eng@example.com",existing_job_numbers=["2026-001"],year=2026)
    assert built["job"]["job_number"]=="2026-002"
    assert built["job"]["source"]=="MIDRA_PROPERTY"
    assert built["job"]["sections"]["property"]["summary"]["property_analysis_engineer_accepted"] is False
    assert built["creation_snapshot"]["engineering_job_created"] is True
    assert built["creation_snapshot"]["property_analysis_engineer_accepted"] is False


def test_bridge_rejects_unapproved_or_declined():
    record,proposal,client=_service_inputs(status="PROPOSAL_GENERATED")
    try:
        build_authorized_engineering_job_creation(property_record=record,proposal_request=proposal,client_response=client,engineering_user="eng",existing_job_numbers=[],year=2026)
    except ValueError as exc:
        assert "CLIENT_APPROVED" in str(exc)
    else: raise AssertionError("expected CLIENT_APPROVED guard")
    record,proposal,client=_service_inputs(response="DECLINED")
    proposal.request_status="CLIENT_APPROVED"
    try:
        build_authorized_engineering_job_creation(property_record=record,proposal_request=proposal,client_response=client,engineering_user="eng",existing_job_numbers=[],year=2026)
    except ValueError as exc:
        assert "ACCEPTED" in str(exc)
    else: raise AssertionError("expected ACCEPTED guard")


def _db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[PropertyRecord.__table__,PropertyEngineeringProposalRequest.__table__,EngineeringPropertyProposalClientResponse.__table__,EngineeringJob.__table__,PropertyEngineeringJobLink.__table__,EngineeringPropertyProposalJobCreation.__table__])
    return sessionmaker(bind=engine)()


def test_repository_creates_job_link_and_audit_once():
    db=_db(); now=datetime.now(timezone.utc)
    db.add(PropertyRecord(property_record_id="p1",canonical_key="x",search_query="1 Main St",display_address="1 Main St",municipality="Howell",county="Monmouth",block="1",lot="2",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=now,updated_at=now))
    db.add(PropertyEngineeringProposalRequest(proposal_request_id="r1",property_record_id="p1",analysis_run_id=None,project_goal="pool",customer_name="Jane",customer_email="jane@example.com",customer_phone=None,request_status="CLIENT_APPROVED",source_product="MIDRA_PROPERTY",destination_product="MIDRA_ENGINEERING",created_at=now))
    db.add(EngineeringPropertyProposalClientResponse(engineering_client_response_id="c1",engineering_release_id="rel1",property_record_id="p1",proposal_request_id="r1",proposal_id="MEP-1",proposal_number="P-1",response_status="ACCEPTED",response_snapshot={"client_response_status":"ACCEPTED","client_approved":True,"engineering_job_created":False,"project":"Pool Engineering"},recorded_by="eng",created_at=now))
    # SQLite FK enforcement is not enabled in this focused repository test; exact referenced release is validated in 2.30 tests.
    db.commit()
    repo=SQLAlchemyEngineeringPropertyProposalJobCreationRepository(db)
    item=repo.create_from_accepted_response(property_record_id="p1",proposal_request_id="r1",engineering_client_response_id="c1",engineering_user="eng@example.com",year=2026)
    assert item.engineering_job_number=="2026-001"
    assert db.get(EngineeringJob,"2026-001").source=="MIDRA_PROPERTY"
    link=db.query(PropertyEngineeringJobLink).filter_by(property_record_id="p1",engineering_job_number="2026-001").one()
    assert link.link_status=="linked"
    again=repo.create_from_accepted_response(property_record_id="p1",proposal_request_id="r1",engineering_client_response_id="c1",engineering_user="eng@example.com",year=2026)
    assert again.engineering_job_creation_id==item.engineering_job_creation_id
    assert db.query(EngineeringJob).count()==1
