from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from api.services import auth_service
from utils.jwt import verify_access_token
from slowapi.util import get_remote_address
from slowapi import Limiter
from fastapi import Request, Depends


router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

def limiter_dep(request:Request) -> Limiter:
    return request.app.state.limiter


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token invalide")
    return authorization.split(" ", 1)[1]

@router.post("/register")
def register(payload: RegisterIn):
    try:
        return auth_service.register(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
        )
    except ValueError as e:
        # Erreur métier lisible
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Ne JAMAIS renvoyer str(e) ici (risque encodage)
        raise HTTPException(status_code=400, detail="Erreur")

@router.post("/login")
def login(payload: LoginIn):
    try:
        return auth_service.login(payload.email, payload.password)
    except ValueError as e:
        # erreurs metier (identifiants invalides, compte désactivé, etc.)
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # ✅ on CAPTURE l'exception pour pouvoir la logguer
        print("[LOGIN-ERROR]", repr(e))
        raise HTTPException(status_code=400, detail="Erreur")

@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = _extract_bearer(authorization)
    try:
        return auth_service.logout(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")

@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    token = _extract_bearer(authorization)
    try:
        return auth_service.get_user_connected(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")
