"""HTTP product surface for persistent MIDRA Engineering operations."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.engineering_persistent_command_center import persistent_command_center

router=APIRouter(prefix="/engineering/command-center",
                 tags=["MIDRA Engineering Command Center"])

@router.get("")
def command_center(state: str | None=None,db: Session=Depends(get_db)):
    return persistent_command_center(db,state=state)
