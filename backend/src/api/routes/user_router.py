from fastapi import APIRouter, HTTPException, Header , Depends
from pydantic import BaseModel
from typing import Optional
from api.services import user_service
from utils.auth import require_roles , require_permissions
from utils.jwt import verify_access_token

router = APIRouter(prefix="/users", tags=["users"])

class UpdateMeIn(BaseModel):
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""

def _require_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant au invalide")
    token = authorization("", 1)[1]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token expire ou introuvable")
    return int(payload["user_id"])

@router.get("/")
def get_all(authorization: Optional[str] = Header(default=None), limit: int = 100, offset: int = 0):
    _require_user_id(authorization)
    return user_service.get_all_users(limit=limit, offset=offset)

@router.get("/{user_id}")
def get_by_id(user_id: int, authorization: Optional[str] = Header(default=None)):
    _require_user_id(authorization)
    try:
        return user_service.get_user_by_id(user_id)
    except ValueError as e :
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/", dependencies=[Depends(require_roles(["admin"]))])
def list_users(limit: int = 100 , offset: int = 0):
    return user_service.get_all_users(limit, offset)
    
@router.put("/me")
def update_me(payload: UpdateMeIn, authorization: Optional[str] = Header(default=None)):
    uid = _require_user_id(authorization)
    try:
        return user_service.update_user(uid, payload.first_name or "", payload.last_name or "")
    except ValueError as e : 
        raise HTTPException(status_code=400, detail=str(e))
    
@router.delete("/{user_id}", dependencies=[Depends(require_permissions(["users.write"]))])
def delete_user(user_id: int):
    return user_service.delete_user(user_id)
    
@router.delete("/{user_id}")
def delete_user(user_id: int , authorization: Optional[str] = Header(default=None)):
    _require_user_id(authorization)
    try:
        return user_service.delete_user(user_id)
    except ValueError as e :
        raise HTTPException(status_code=404, detail=str(e))