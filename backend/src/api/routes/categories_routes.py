from fastapi import APIRouter, Query, HTTPException, Header, Depends
from typing import Optional
from schema.category import CategoryIn, CategoryOut, CategoryListOut, CategoryUpdate
from api.services import categorie_service as svc
from utils.auth import require_permissions

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("/", dependencies=[Depends(require_permissions(["protocols.read"]))])
def list_categories(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), q: Optional[str]=Query(None)):
    return svc.list_categories(limit, offset, q)

@router.get("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_permissions(["protocols.read"]))])
def get_category(category_id: int):
    try:
        return svc.get_category(category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_permissions(["protocols.write"]))])
def create_category(payload: CategoryIn):
    try:
        return svc.create_category(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_permissions(["protocols.write"]))])
def patch_category(category_id: int, payload: CategoryUpdate):
    try:
        return svc.update_category(category_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{category_id}", status_code=204, dependencies=[Depends(require_permissions(["protocols.write"]))])
def remove_category(category_id: int):
    try:
        svc.delete_category(category_id)
        return
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
