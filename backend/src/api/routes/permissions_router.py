from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from api.services import permission_service as svc
from schema.permissions import PermissionCreateIn, PermissionListOut, PermissionOut, PermissionUpdateIn
from utils.auth import require_any_role


router = APIRouter(prefix="/permissions", tags=["permissions"])

ADMIN_ROLES = ["admin", "permissions_manager"]


@router.get(
    "/",
    response_model=PermissionListOut,
    dependencies=[Depends(require_any_role(ADMIN_ROLES))],
)
def list_permissions(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(default=None),
):
    try:
        return svc.list_permissions(limit=limit, offset=offset, q=q)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/roles/{role_id}", dependencies=[Depends(require_any_role(ADMIN_ROLES))])
def list_permissions_of_role(role_id: int):
    try: 
        return svc.list_permission_from_role(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{perm_code}/roles", dependencies=[Depends(require_any_role(ADMIN_ROLES))])
def list_roles_having_permission(perm_code: str):
    try:
        return svc.list_role_from_permission(perm_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/roles/{role_id}/{perm_code}", dependencies=[Depends(require_any_role(ADMIN_ROLES))])
def link_permission_to_role(role_id: int, perm_code: str):
    try:
        return svc.add_permission_to_role(role_id, perm_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    

@router.get("/{code}", response_model=PermissionOut, dependencies=[Depends(require_any_role(ADMIN_ROLES))])
def get_permission(code: str):
    row = svc.permission_controller.get_permission_by_code(code)
    if not row: 
        raise HTTPException(status_code=404, detail="Permission inconnue")
    return PermissionOut(
       id=row[0], code=row[1], label=row[2], description=row[3],
        created_at=row[4], updated_at=row[5]  
    )


@router.post(
    "/",
    response_model=PermissionOut,
    status_code=201,
    dependencies=[Depends(require_any_role(ADMIN_ROLES))],
)
def create_permission(payload: PermissionCreateIn):
    try:
        created = svc.create_permission(payload.code, payload.label, payload.description)
        row = svc.permission_controller.get_permission_by_code(created["code"])
        return PermissionOut(
            id=row[0], code=row[1], label=row[2], description=row[3],
            created_at=row[4], updated_at=row[5]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")


@router.put(
    "/{code}",
    dependencies=[Depends(require_any_role(ADMIN_ROLES))],
)
def update_permission(code: str, payload: PermissionUpdateIn):
    try:
        return svc.update_permission(code, payload.label, payload.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")


@router.delete(
    "/{code}",
    status_code=204,
    dependencies=[Depends(require_any_role(ADMIN_ROLES))],
)
def delete_permission(code: str):
    try:
        svc.delete_permission(code)
        return  
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Erreur")
    
@router.delete("/roles/{role_id}/{perm_code}", dependencies=[Depends(require_any_role(ADMIN_ROLES))])
def unlink_permission_from_role(role_id: int, perm_code: str):
    try:
        return svc.remove_permission_from_role(role_id, perm_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    