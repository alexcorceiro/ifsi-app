from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from api.services import auth_service
from utils.auth import extract_bearer
from slowapi import Limiter
from fastapi import Request, Depends
from schema.auth import LoginIn, RegisterIn, UserOut



router = APIRouter(prefix="/auth", tags=["auth"])

def limiter_dep(request:Request) -> Limiter:
    return request.app.state.limiter


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token invalide")
    return authorization.split(" ", 1)[1]

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn):
    try:
        user = auth_service.register(payload) 
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Erreur d'inscription")

@router.post("/login")
def login(payload: LoginIn):
    return auth_service.login(payload)

@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = extract_bearer(authorization)
    try:
        return auth_service.logout(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")

@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    try:
        token = extract_bearer(authorization)
        return auth_service.me_from_access_token(token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")