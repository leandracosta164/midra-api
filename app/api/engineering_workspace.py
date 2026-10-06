"""MIDRA Engineering workspace HTTP endpoints."""
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.engineering_workspace_dashboard import (
    engineering_dashboard,load_engineering_workspace
)

router=APIRouter(prefix="/engineering/workspace",tags=["MIDRA Engineering Workspace"])

@router.get("")
def dashboard(state: str | None=None,db: Session=Depends(get_db)):
    return engineering_dashboard(db,state=state)

@router.get("/{job_number}")
def workspace(job_number: str,db: Session=Depends(get_db)):
    try:
        return load_engineering_workspace(db,job_number)
    except KeyError as exc:
        raise HTTPException(status_code=404,detail="engineering job not found") from exc
