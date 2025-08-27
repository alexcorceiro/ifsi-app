from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from utils.auth import require_permissions
from api.services import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])

class PermissionCreateIn(BaseModel):
    code: str
    label: str
    description: Optional[str] = None

class PermissionUpdateIn(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None

@router.get("/", dependencies=[Depends(require_permissions(["roles.read"]))])
def list_permissions(limit: int = 100, offset: int = 0, q: Optional[str]= Query(default=None)):
    return permission_service.list_permissions(limit, offset, q)

@router.post("/", dependencies=[Depends(require_permissions(["roles.write"]))])
def create_permission(payload: PermissionCreateIn):
    try: 
        return permission_service.create_permission(payload.code, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/{code}", dependencies=[Depends(require_permissions(["roles.write"]))])
def update_permission(code: str, payload: PermissionUpdateIn):
    try: 
        return permission_service.update_permission(code, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{code}", dependencies=[Depends(require_permissions(["roles.write"]))])
def delete_permission(code: str):
    try: 
        return permission_service.delete_permission(code)
    except ValueError as e: 
        raise HTTPException(status_code=404, detail=str(e))