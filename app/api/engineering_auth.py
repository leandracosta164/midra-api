"""Login/session endpoints for the MIDRA Engineering workplace."""
from fastapi import APIRouter,Depends,HTTPException,Request,Response,status
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.core.engineering_security import (
    COOKIE_NAME,authenticate_credentials,create_session,credentials_configured,
    delete_session,require_engineering_user,
)
from app.db.session import get_db

router=APIRouter(prefix="/engineering/auth",tags=["MIDRA Engineering Authentication"])

class LoginRequest(BaseModel):
    email: str=Field(min_length=3,max_length=320)
    password: str=Field(min_length=1,max_length=500)

@router.get("/status")
def auth_status():
    return {"configured":credentials_configured()}

@router.post("/login")
def login(payload: LoginRequest,response: Response,db: Session=Depends(get_db)):
    if not credentials_configured():
        raise HTTPException(status_code=503,
            detail="engineering workplace credentials are not configured")
    if not authenticate_credentials(payload.email,payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="invalid credentials")
    raw,_=create_session(db,payload.email)
    response.set_cookie(
        key=COOKIE_NAME,value=raw,httponly=True,samesite="lax",
        secure=settings.APP_ENV.lower() not in {"development","dev","local"},
        max_age=settings.MIDRA_ENGINEERING_SESSION_HOURS*3600,path="/",
    )
    return {"authenticated":True,"email":payload.email.strip().casefold()}

@router.post("/logout")
def logout(request: Request,response: Response,db: Session=Depends(get_db)):
    delete_session(db,request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME,path="/")
    return {"authenticated":False}

@router.get("/me")
def me(email: str=Depends(require_engineering_user)):
    return {"authenticated":True,"email":email}

