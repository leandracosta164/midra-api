"""Login/session endpoints for the MIDRA Property workspace."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.property_security import (
    COOKIE_NAME,
    authenticate_credentials,
    create_session_token,
    credentials_configured,
    require_property_user,
)
from app.core.settings import settings

router = APIRouter(prefix="/property/auth", tags=["MIDRA Property Authentication"])


class PropertyLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=500)


@router.get("/status")
def auth_status():
    return {"configured": credentials_configured()}


@router.post("/login")
def login(payload: PropertyLoginRequest, response: Response):
    if not credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="property workspace credentials are not configured",
        )
    if not authenticate_credentials(payload.email, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    email = payload.email.strip().casefold()
    token = create_session_token(email)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.APP_ENV.lower() not in {"development", "dev", "local"},
        max_age=settings.MIDRA_PROPERTY_SESSION_HOURS * 3600,
        path="/",
    )
    return {"authenticated": True, "email": email, "role": "PROPERTY_ADMIN"}


@router.post("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"authenticated": False}


@router.get("/me")
def me(email: str = Depends(require_property_user)):
    return {"authenticated": True, "email": email, "role": "PROPERTY_ADMIN"}
