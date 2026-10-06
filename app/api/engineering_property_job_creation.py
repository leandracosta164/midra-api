"""Protected authorized Engineering job creation for accepted Property-origin proposals."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.engineering_security import require_engineering_user
from app.db.session import get_db
from app.models.engineering_job import EngineeringJob
from app.models.property_engineering_job_link import PropertyEngineeringJobLink
from app.models.property_engineering_proposal_request import PropertyEngineeringProposalRequest
from app.repositories.engineering_property_proposal_job_creation import SQLAlchemyEngineeringPropertyProposalJobCreationRepository
from app.schemas.engineering_property_job_creation import EngineeringPropertyProposalJobCreationActionRead

router=APIRouter(prefix="/engineering/property-proposals",tags=["MIDRA Engineering Property Proposals"])


def _action_payload(db: Session, item):
    job=db.get(EngineeringJob,item.engineering_job_number)
    link=db.scalar(select(PropertyEngineeringJobLink).where(
        PropertyEngineeringJobLink.property_record_id==item.property_record_id,
        PropertyEngineeringJobLink.engineering_job_number==item.engineering_job_number,
        PropertyEngineeringJobLink.link_status=="linked",
    ))
    request=db.get(PropertyEngineeringProposalRequest,item.proposal_request_id)
    if job is None or link is None or request is None:
        raise HTTPException(status_code=409,detail="Engineering job creation audit is incomplete")
    return {
        "job_creation":item,
        "engineering_job":job,
        "property_link":link,
        "proposal_request_status":request.request_status,
        "engineering_job_created":True,
        "property_analysis_engineer_accepted":False,
    }


@router.post(
    "/{property_record_id}/{proposal_request_id}/client-responses/{engineering_client_response_id}/create-job",
    response_model=EngineeringPropertyProposalJobCreationActionRead,
)
def create_engineering_job_from_accepted_property_proposal(
    property_record_id: str,
    proposal_request_id: str,
    engineering_client_response_id: str,
    db: Session=Depends(get_db),
    engineering_user: str=Depends(require_engineering_user),
):
    """Create exactly one Engineering job after explicit client acceptance.

    The job and Property link are written atomically. Property analysis remains unaccepted
    until a separate authorized Engineering review explicitly accepts it.
    """
    try:
        item=SQLAlchemyEngineeringPropertyProposalJobCreationRepository(db).create_from_accepted_response(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
            engineering_client_response_id=engineering_client_response_id,
            engineering_user=engineering_user,
        )
        return _action_payload(db,item)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="accepted proposal context not found") from exc
    except (ValueError,PermissionError) as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc


@router.get(
    "/{property_record_id}/{proposal_request_id}/job-creation",
    response_model=EngineeringPropertyProposalJobCreationActionRead,
)
def get_engineering_job_creation_for_property_proposal(
    property_record_id: str,
    proposal_request_id: str,
    db: Session=Depends(get_db),
    engineering_user: str=Depends(require_engineering_user),
):
    _=engineering_user
    try:
        item=SQLAlchemyEngineeringPropertyProposalJobCreationRepository(db).get_for_proposal(
            property_record_id=property_record_id,
            proposal_request_id=proposal_request_id,
        )
        return _action_payload(db,item)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="Engineering job has not been created for this proposal") from exc
