from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.engineering_property_proposal_draft import EngineeringPropertyProposalDraft
from app.repositories.engineering_property_proposal_draft import SQLAlchemyEngineeringPropertyProposalDraftRepository


def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            PropertyRecord.__table__,
            PropertyAnalysisRun.__table__,
            PropertyEngineeringProposalRequest.__table__,
            EngineeringPropertyProposalDraft.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def seed(session):
    record=PropertyRecord(
        property_record_id="p1",canonical_key="x",search_query="1 Main St",
        display_address="1 Main St",municipality="Example",county="County",
        block="1",lot="2",latitude=None,longitude=None,
        intelligence_status="MIDRA_ANALYSIS",latest_analysis={},
        created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc),
    )
    proposal=PropertyEngineeringProposalRequest(
        proposal_request_id="r1",property_record_id="p1",analysis_run_id=None,
        project_goal="pool",customer_name="Jane",customer_email="jane@example.com",
        customer_phone=None,request_status="REQUESTED",
        source_product="MIDRA_PROPERTY",destination_product="MIDRA_ENGINEERING",
        created_at=datetime.now(timezone.utc),
    )
    session.add_all([record,proposal]); session.commit()


def draft():
    return {
        "proposal_id":"MEP-ABC",
        "proposal_number":"P-2026-001",
        "status":"DRAFT_REQUIRES_ENGINEER_REVIEW",
        "total_price":"2500.00",
        "send_allowed":False,
        "engineering_job_created":False,
    }


def test_create_get_and_list_exact_durable_draft():
    session=db(); seed(session)
    repo=SQLAlchemyEngineeringPropertyProposalDraftRepository(session)
    item=repo.create(
        property_record_id="p1",proposal_request_id="r1",
        draft_snapshot=draft(),generated_by="engineer@midra.local",
    )
    assert item.engineering_draft_id
    assert item.proposal_status=="DRAFT_REQUIRES_ENGINEER_REVIEW"
    assert item.draft_snapshot["total_price"]=="2500.00"
    fetched=repo.get(
        property_record_id="p1",proposal_request_id="r1",
        engineering_draft_id=item.engineering_draft_id,
    )
    assert fetched.engineering_draft_id==item.engineering_draft_id
    assert repo.list(property_record_id="p1",proposal_request_id="r1")[0].proposal_number=="P-2026-001"


def test_repository_refuses_non_review_draft():
    session=db(); seed(session)
    bad=draft(); bad["status"]="APPROVED_READY_TO_SEND"
    try:
        SQLAlchemyEngineeringPropertyProposalDraftRepository(session).create(
            property_record_id="p1",proposal_request_id="r1",
            draft_snapshot=bad,generated_by="engineer@midra.local",
        )
    except ValueError as exc:
        assert "only review-required" in str(exc)
    else:
        raise AssertionError("approved payload must not enter draft workspace")


def test_repository_enforces_property_request_ownership():
    session=db(); seed(session)
    try:
        SQLAlchemyEngineeringPropertyProposalDraftRepository(session).create(
            property_record_id="wrong",proposal_request_id="r1",
            draft_snapshot=draft(),generated_by="engineer@midra.local",
        )
    except KeyError as exc:
        assert exc.args[0]=="proposal_request"
    else:
        raise AssertionError("cross-property draft persistence must fail")
