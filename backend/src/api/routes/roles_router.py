from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from utils.auth import require_permissions
from fastapi import Depends
from api.services import role_service

router = APIRouter(prefix="/roles", tags=["roles"])

class RoleCreateIn(BaseModel):
    code: str
    label: str
    description: Optional[str] = None

class RoleUpdateIn(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None

@router.get("/", dependencies=[Depends(require_permissions(["roles.read"]))])
def list_roles(limit: int = 50, offset: int = 0, q: Optional[str] = Query(default=None)):
    return role_service.list_roles(limit, offset, q)

@router.get("/{role_id}", dependencies=[Depends(require_permissions(["roles.read"]))])
def get_role(role_id: int):
    try: 
        return role_service.get_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/", dependencies=[Depends(require_permissions(["roles.write"]))])
def create_role(payload: RoleCreateIn):
    try:
        return role_service.create_role(payload.code, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/{role_id}", dependencies=[Depends(require_permissions(["roles.write"]))])
def update_role(role_id: int, payload: RoleUpdateIn):
    try: 
        return role_service.update_role(role_id, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{role_id}", dependencies=[Depends(require_permissions(["roles.write"]))])
def delete_role(role_id: int):
    try:
        return role_service.delete_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/permissions/{perm_code}", dependencies=[Depends(require_permissions(["roles.write"]))])
def add_permission(role_id: int, perm_code: str):
    try:
        return role_service.add_permission(role_id, perm_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/permissions/{perm_code}", dependencies=[Depends(require_permissions(["roles.write"]))])
def remove_permission(role_id: int, perm_code: str):
    try:
         return role_service.remove_permission(role_id, perm_code)
    except ValueError as e :
        raise HTTPException(status_code=404, detail=str(e))