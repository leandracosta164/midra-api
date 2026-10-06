from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.models.engineering_property_proposal_review import EngineeringPropertyProposalReview
from app.repositories.engineering_property_proposal_review import SQLAlchemyEngineeringPropertyProposalReviewRepository

def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[PropertyRecord.__table__,PropertyEngineeringProposalRequest.__table__,EngineeringPropertyProposalDraft.__table__,EngineeringPropertyProposalReview.__table__])
    return sessionmaker(bind=engine)()

def seed(session):
    record=PropertyRecord(property_record_id="p1",canonical_key="x",search_query="1 Main St",display_address="1 Main St",municipality="Example",county="County",block="1",lot="2",latitude=None,longitude=None,intelligence_status="MIDRA_ANALYSIS",latest_analysis={},created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc))
    request=PropertyEngineeringProposalRequest(proposal_request_id="r1",property_record_id="p1",analysis_run_id=None,project_goal="pool",customer_name="Jane",customer_email="jane@example.com",customer_phone=None,request_status="REQUESTED",source_product="MIDRA_PROPERTY",destination_product="MIDRA_ENGINEERING",created_at=datetime.now(timezone.utc))
    draft=EngineeringPropertyProposalDraft(engineering_draft_id="d1",property_record_id="p1",proposal_request_id="r1",proposal_id="MEP-ABC",proposal_number="P-2026-001",proposal_status="DRAFT_REQUIRES_ENGINEER_REVIEW",draft_snapshot={"proposal_id":"MEP-ABC","proposal_number":"P-2026-001","status":"DRAFT_REQUIRES_ENGINEER_REVIEW"},generated_by="eng@example.com",created_at=datetime.now(timezone.utc))
    session.add_all([record,request,draft]); session.commit()

def approved():
    return {"proposal_id":"MEP-ABC","proposal_number":"P-2026-001","status":"APPROVED_READY_TO_SEND","send_allowed":True,"sent":False,"engineering_job_created":False}

def test_create_approval_is_durable_atomic_and_idempotent():
    s=db(); seed(s); repo=SQLAlchemyEngineeringPropertyProposalReviewRepository(s)
    item=repo.create_approval(property_record_id="p1",proposal_request_id="r1",engineering_draft_id="d1",approved_snapshot=approved(),reviewed_by="eng@example.com")
    assert item.review_status=="APPROVED_READY_TO_SEND"
    assert s.get(PropertyEngineeringProposalRequest,"r1").request_status=="PROPOSAL_GENERATED"
    again=repo.create_approval(property_record_id="p1",proposal_request_id="r1",engineering_draft_id="d1",approved_snapshot=approved(),reviewed_by="eng@example.com")
    assert again.engineering_review_id==item.engineering_review_id
    assert len(repo.list(property_record_id="p1",proposal_request_id="r1"))==1

def test_refuses_unapproved_or_sent_snapshot():
    s=db(); seed(s); repo=SQLAlchemyEngineeringPropertyProposalReviewRepository(s)
    bad=approved(); bad["status"]="DRAFT_REQUIRES_ENGINEER_REVIEW"
    try: repo.create_approval(property_record_id="p1",proposal_request_id="r1",engineering_draft_id="d1",approved_snapshot=bad,reviewed_by="eng@example.com")
    except ValueError as exc: assert "engineer-approved" in str(exc)
    else: raise AssertionError("unapproved snapshot accepted")

def test_exact_draft_ownership_is_enforced():
    s=db(); seed(s); repo=SQLAlchemyEngineeringPropertyProposalReviewRepository(s)
    try: repo.create_approval(property_record_id="wrong",proposal_request_id="r1",engineering_draft_id="d1",approved_snapshot=approved(),reviewed_by="eng@example.com")
    except KeyError as exc: assert exc.args[0]=="engineering_draft"
    else: raise AssertionError("cross-property approval accepted")
