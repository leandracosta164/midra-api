"""Protected MIDRA Workplace portfolio API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.engineering_workplace_portfolio import (
    engineering_workplace_portfolio,
    engineering_workplace_proposal_detail,
    engineering_workplace_job_detail,
    engineering_workplace_search,
    engineering_workplace_property_detail,
    engineering_workplace_property_evidence,
)

router=APIRouter(prefix="/engineering/workplace",tags=["MIDRA Workplace"])


@router.get("/portfolio")
def workplace_portfolio(db: Session=Depends(get_db)):
    return engineering_workplace_portfolio(db)


@router.get("/search")
def workplace_search(
    q: str = "",
    limit: int = 12,
    db: Session=Depends(get_db),
):
    return engineering_workplace_search(db, q, limit=limit)


@router.get("/properties/{property_record_id}")
def workplace_property_detail(
    property_record_id: str,
    analysis_run_id: str | None = None,
    db: Session=Depends(get_db),
):
    try:
        return engineering_workplace_property_detail(db, property_record_id, analysis_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workplace Property record not found.")


@router.get("/properties/{property_record_id}/evidence")
def workplace_property_evidence(
    property_record_id: str,
    analysis_run_id: str | None = None,
    db: Session=Depends(get_db),
):
    try:
        return engineering_workplace_property_evidence(db, property_record_id, analysis_run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workplace Property record not found.")


@router.get("/proposals/{proposal_request_id}")
def workplace_proposal_detail(
    proposal_request_id: str,
    db: Session=Depends(get_db),
):
    try:
        return engineering_workplace_proposal_detail(db, proposal_request_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workplace proposal request not found.")


@router.get("/jobs/{engineering_job_number}")
def workplace_job_detail(
    engineering_job_number: str,
    db: Session=Depends(get_db),
):
    try:
        return engineering_workplace_job_detail(db, engineering_job_number)
    except KeyError:
        raise HTTPException(status_code=404, detail="Workplace Engineering job not found.")
