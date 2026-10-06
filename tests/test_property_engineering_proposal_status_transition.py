from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.property_record import PropertyRecord
from app.repositories.property_engineering_proposal_request import (
    SQLAlchemyPropertyEngineeringProposalRequestRepository,
)


def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def property_record(session):
    item=PropertyRecord(
        property_record_id="p1", canonical_key="x", search_query="1 Main St",
        display_address="1 Main St", municipality="Howell", county="Monmouth",
        block="1", lot="2", latitude=None, longitude=None,
        intelligence_status="MIDRA_ANALYSIS", latest_analysis={},
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    session.add(item); session.commit()


def proposal(session):
    property_record(session)
    return SQLAlchemyPropertyEngineeringProposalRequestRepository(session).create(
        property_record_id="p1", analysis_run_id=None, project_goal="pool",
        customer_name="Jane", customer_email="jane@example.com",
    )


def test_requested_to_generated_is_allowed():
    session=db(); item=proposal(session)
    repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(session)
    updated=repo.transition_status(
        property_record_id="p1",
        proposal_request_id=item.proposal_request_id,
        expected_current_status="REQUESTED",
        next_status="PROPOSAL_GENERATED",
    )
    assert updated.request_status=="PROPOSAL_GENERATED"


def test_direct_requested_to_client_approved_is_rejected():
    session=db(); item=proposal(session)
    repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(session)
    try:
        repo.transition_status(
            property_record_id="p1",
            proposal_request_id=item.proposal_request_id,
            expected_current_status="REQUESTED",
            next_status="CLIENT_APPROVED",
        )
    except ValueError as exc:
        assert exc.args[0]=="proposal_transition_not_allowed"
    else:
        raise AssertionError("invalid lifecycle jump must be rejected")


def test_stale_expected_status_is_rejected():
    session=db(); item=proposal(session)
    repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(session)
    try:
        repo.transition_status(
            property_record_id="p1",
            proposal_request_id=item.proposal_request_id,
            expected_current_status="PROPOSAL_GENERATED",
            next_status="CLIENT_APPROVED",
        )
    except ValueError as exc:
        assert exc.args[0]=="proposal_status_changed"
    else:
        raise AssertionError("stale status write must be rejected")
