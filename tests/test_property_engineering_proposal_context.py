from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.property_analysis_run import PropertyAnalysisRun
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.models.property_record import PropertyRecord
from app.repositories.property_engineering_proposal_request import SQLAlchemyPropertyEngineeringProposalRequestRepository
from app.services.property_engineering_proposal_context import build_property_engineering_proposal_context


def db():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            PropertyRecord.__table__,
            PropertyAnalysisRun.__table__,
            PropertyEngineeringProposalRequest.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def property_record(session):
    item=PropertyRecord(
        property_record_id="p1",canonical_key="x",search_query="1 Main St",
        display_address="1 Main St",municipality="Howell",county="Monmouth",
        block="1",lot="2",latitude=None,longitude=None,
        intelligence_status="MIDRA_ANALYSIS",latest_analysis={},
        created_at=datetime.now(timezone.utc),updated_at=datetime.now(timezone.utc),
    )
    session.add(item);session.commit();return item


def test_repository_get_resolves_only_request_owned_by_property():
    session=db();property_record(session)
    repo=SQLAlchemyPropertyEngineeringProposalRequestRepository(session)
    created=repo.create(
        property_record_id="p1",analysis_run_id=None,project_goal="pool",
        customer_name="Jane",customer_email="jane@example.com",
    )
    assert repo.get("p1",created.proposal_request_id).proposal_request_id==created.proposal_request_id
    try:
        repo.get("p1","missing")
    except KeyError as exc:
        assert exc.args[0]=="proposal_request"
    else:
        raise AssertionError("expected proposal request ownership check")


def test_context_reuses_durable_analysis_and_preserves_professional_boundary():
    analysis=SimpleNamespace(
        analysis_run_id="a1",
        property_record_id="p1",
        analysis={
            "verification_items":["VERIFY wetlands"],
            "environmental_verification_items":["VERIFY wetlands"],
            "zoning_candidate_verification_items":[],
        },
    )
    proposal=SimpleNamespace(proposal_request_id="r1",property_record_id="p1")
    record=SimpleNamespace(property_record_id="p1")
    context=build_property_engineering_proposal_context(
        proposal_request=proposal,property_record=record,analysis_run=analysis,
    )
    assert context["status"]=="PROPERTY_ENGINEERING_PROPOSAL_CONTEXT_READY"
    assert context["analysis_run"] is analysis
    assert context["verification_summary"]["status"]=="VERIFICATION_REQUIRED"
    assert context["professional_boundary"]["engineer_reviewed"] is False
    assert context["professional_boundary"]["engineer_accepted"] is False
    assert context["engineering_job_created"] is False


def test_context_without_analysis_is_property_only_and_does_not_invent_analysis():
    context=build_property_engineering_proposal_context(
        proposal_request=SimpleNamespace(proposal_request_id="r1"),
        property_record=SimpleNamespace(property_record_id="p1"),
        analysis_run=None,
    )
    assert context["status"]=="PROPERTY_ENGINEERING_PROPOSAL_CONTEXT_PROPERTY_ONLY"
    assert context["analysis_run"] is None
    assert context["verification_summary"]=={}
    assert context["engineering_job_created"] is False
