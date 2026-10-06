from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.engineering_property_proposal_client_response import EngineeringPropertyProposalClientResponse
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.property_record import PropertyRecord
from app.repositories.engineering_property_proposal_client_response import SQLAlchemyEngineeringPropertyProposalClientResponseRepository


def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[
        PropertyRecord.__table__,
        PropertyEngineeringProposalRequest.__table__,
        EngineeringPropertyProposalDraft.__table__,
        EngineeringPropertyProposalReview.__table__,
        EngineeringPropertyProposalRelease.__table__,
        EngineeringPropertyProposalClientResponse.__table__,
    ])
    return sessionmaker(bind=engine)()


def seed(session):
    now=datetime.now(timezone.utc)
    session.add(PropertyRecord(
        property_record_id="p1",canonical_key="x",search_query="1 Main St",
        display_address="1 Main St",municipality="Howell",county="Monmouth",
        block="1",lot="2",latitude=None,longitude=None,
        intelligence_status="MIDRA_ANALYSIS",latest_analysis={},
        created_at=now,updated_at=now,
    ))
    session.add(PropertyEngineeringProposalRequest(
        proposal_request_id="r1",property_record_id="p1",analysis_run_id=None,
        project_goal="pool",customer_name="Jane",customer_email="jane@example.com",
        customer_phone=None,request_status="PROPOSAL_GENERATED",
        source_product="MIDRA_PROPERTY",destination_product="MIDRA_ENGINEERING",
        created_at=now,
    ))
    session.add(EngineeringPropertyProposalDraft(
        engineering_draft_id="d1",property_record_id="p1",proposal_request_id="r1",
        proposal_id="MEP-1",proposal_number="P-001",
        proposal_status="DRAFT_REQUIRES_ENGINEER_REVIEW",draft_snapshot={},
        generated_by="eng",created_at=now,
    ))
    session.add(EngineeringPropertyProposalReview(
        engineering_review_id="v1",engineering_draft_id="d1",
        property_record_id="p1",proposal_request_id="r1",
        proposal_id="MEP-1",proposal_number="P-001",
        review_status="APPROVED_READY_TO_SEND",approved_snapshot={},
        reviewed_by="eng",created_at=now,
    ))
    session.add(EngineeringPropertyProposalRelease(
        engineering_release_id="x1",engineering_review_id="v1",
        property_record_id="p1",proposal_request_id="r1",
        proposal_id="MEP-1",proposal_number="P-001",
        release_status="SENT_AWAITING_CLIENT_RESPONSE",
        released_snapshot={"status":"SENT","sent":True,"proposal_id":"MEP-1","client_response_status":"AWAITING_CLIENT_RESPONSE"},
        released_by="eng",created_at=now,
    ))
    session.commit()


def snapshot(response):
    return {
        "status":"SENT",
        "sent":True,
        "proposal_id":"MEP-1",
        "client_response_status":response,
        "client_approved":response=="ACCEPTED",
        "engineering_job_created":False,
    }


def test_acceptance_advances_lifecycle_without_creating_job():
    s=db(); seed(s)
    repo=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(s)
    item=repo.create_response(
        property_record_id="p1",proposal_request_id="r1",engineering_release_id="x1",
        response_snapshot=snapshot("ACCEPTED"),recorded_by="eng",
    )
    assert item.response_status=="ACCEPTED"
    assert s.get(PropertyEngineeringProposalRequest,"r1").request_status=="CLIENT_APPROVED"
    assert item.response_snapshot["engineering_job_created"] is False


def test_decline_advances_to_declined():
    s=db(); seed(s)
    repo=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(s)
    item=repo.create_response(
        property_record_id="p1",proposal_request_id="r1",engineering_release_id="x1",
        response_snapshot=snapshot("DECLINED"),recorded_by="eng",
    )
    assert item.response_status=="DECLINED"
    assert s.get(PropertyEngineeringProposalRequest,"r1").request_status=="DECLINED"


def test_response_is_idempotent_per_exact_release():
    s=db(); seed(s)
    repo=SQLAlchemyEngineeringPropertyProposalClientResponseRepository(s)
    a=repo.create_response(
        property_record_id="p1",proposal_request_id="r1",engineering_release_id="x1",
        response_snapshot=snapshot("ACCEPTED"),recorded_by="eng",
    )
    b=repo.create_response(
        property_record_id="p1",proposal_request_id="r1",engineering_release_id="x1",
        response_snapshot=snapshot("ACCEPTED"),recorded_by="eng",
    )
    assert a.engineering_client_response_id==b.engineering_client_response_id
