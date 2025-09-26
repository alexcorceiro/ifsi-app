from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel
from utils.auth import require_permissions
from api.services import role_service
from schema.role import RoleCreateIn, RolesListOut, RoleUpdateIn, RoleOut


router = APIRouter(prefix="/roles", tags=["roles"])

class PermissionCodes(BaseModel):
    permission_codes: List[str]

@router.get("/", response_model=RolesListOut, dependencies=[Depends(require_permissions(["role.read"]))])
def list_roles(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), q: Optional[str] = Query(default=None)):
    try:
        return role_service.list_roles(limit, offset, q)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/{role_id}", response_model=RoleOut, dependencies=[Depends(require_permissions(["role.read"]))])
def get_role(role_id: int):
    try:
        return role_service.get_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

   
@router.post("/", dependencies=[Depends(require_permissions(["role.write"]))])
def create_role(payload: RoleCreateIn):
    try:
        return role_service.create_role(payload.code, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/{role_id}", dependencies=[Depends(require_permissions(["role.write"]))])
def update_role(role_id: int, payload: RoleUpdateIn):
    try: 
        return role_service.update_role(role_id, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{role_id}", dependencies=[Depends(require_permissions(["role.write"]))])
def delete_role(role_id: int):
    try:
        return role_service.delete_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/permissions/{perm_code}", dependencies=[Depends(require_permissions(["role.write"]))])
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