from fastapi import APIRouter, Query, HTTPException, Header, Depends
from typing import Optional
from schema.category import CategoryIn, CategoryOut, CategoryListOut, CategoryUpdate
from api.services import categorie_service as svc
from utils.auth import require_permissions

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=CategoryListOut, dependencies=[Depends(require_permissions(["protocols.read"]))])
def list_categories(
    q: Optional[str] = Query(default=None, description="Recherche sur code/label"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    total, items = svc.list_categories(q, limit, offset)
    return {"total": total, "items": items, "limit": limit, "offset": offset}

@router.get("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_permissions("protocol.read"))])
def get_category(category_id: int):
    try:
        return svc.get_category(category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("",response_model=CategoryOut, status_code=201, dependencies=[Depends(require_permissions("protocol.write"))])
def create_category(payload: CategoryIn):
    try:
        return svc.create_category(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_permissions("protocol.write"))])
def patch_category(category_id: int, payload: CategoryUpdate):
    try:
        return svc.update_category(category_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{category_id}", status_code=204, dependencies=[Depends(require_permissions("protocol.write"))])
def remove_category(category_id: int):
    try:
        svc.delete_category(category_id)
        return
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))