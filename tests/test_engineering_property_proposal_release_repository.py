from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.models.engineering_property_proposal_release import EngineeringPropertyProposalRelease
from app.repositories.engineering_property_proposal_release import SQLAlchemyEngineeringPropertyProposalReleaseRepository

def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[
        PropertyRecord.__table__,PropertyEngineeringProposalRequest.__table__,
        EngineeringPropertyProposalDraft.__table__,EngineeringPropertyProposalReview.__table__,
        EngineeringPropertyProposalRelease.__table__,
    ])
    return sessionmaker(bind=engine)()

def seed(session):
    now=datetime.now(timezone.utc)
    session.add(PropertyRecord(property_record_id="p1",canonical_key="x",search_query="x",display_address="1 Main",municipality="Howell",county="Monmouth",block="1",lot="2",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=now,updated_at=now))
    session.add(PropertyEngineeringProposalRequest(proposal_request_id="r1",property_record_id="p1",analysis_run_id=None,project_goal="pool",customer_name="Jane",customer_email="jane@example.com",customer_phone=None,request_status="PROPOSAL_GENERATED",source_product="MIDRA_PROPERTY",destination_product="MIDRA_ENGINEERING",created_at=now))
    session.add(EngineeringPropertyProposalDraft(engineering_draft_id="d1",property_record_id="p1",proposal_request_id="r1",proposal_id="MEP-1",proposal_number="P-1",proposal_status="DRAFT_REQUIRES_ENGINEER_REVIEW",draft_snapshot={"status":"DRAFT_REQUIRES_ENGINEER_REVIEW"},generated_by="eng",created_at=now))
    session.add(EngineeringPropertyProposalReview(engineering_review_id="v1",engineering_draft_id="d1",property_record_id="p1",proposal_request_id="r1",proposal_id="MEP-1",proposal_number="P-1",review_status="APPROVED_READY_TO_SEND",approved_snapshot={"status":"APPROVED_READY_TO_SEND","send_allowed":True,"sent":False,"proposal_id":"MEP-1"},reviewed_by="eng",created_at=now))
    session.commit()

def test_release_is_immutable_idempotent_and_does_not_advance_client_approval():
    s=db();seed(s);repo=SQLAlchemyEngineeringPropertyProposalReleaseRepository(s)
    snap={"status":"SENT","sent":True,"send_allowed":False,"proposal_id":"MEP-1"}
    a=repo.create_release(property_record_id="p1",proposal_request_id="r1",engineering_review_id="v1",released_snapshot=snap,released_by="eng")
    b=repo.create_release(property_record_id="p1",proposal_request_id="r1",engineering_review_id="v1",released_snapshot=snap,released_by="eng")
    assert a.engineering_release_id==b.engineering_release_id
    assert a.release_status=="SENT_AWAITING_CLIENT_RESPONSE"
    request=s.get(PropertyEngineeringProposalRequest,"r1")
    assert request.request_status=="PROPOSAL_GENERATED"
