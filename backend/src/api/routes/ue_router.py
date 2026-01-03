from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import require_permissions
from api.services import ue_service as svc
from schema.ue import UECreateIn, UEUpdateIn, UEOut, UEListOut

router = APIRouter(prefix="/ue", tags=["ue"])

@router.get("/", response_model=UEListOut, dependencies=[Depends(require_permissions(["ue.read"]))])
def list_ue(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
            q: Optional[str] = Query(None), program_id: Optional[int] = Query(None),
            year_no: Optional[int] = Query(None), sem_no: Optional[int] = Query(None)):
    return svc.list_ue(limit, offset, q, program_id, year_no, sem_no)

@router.get("/{ue_id}", response_model=UEOut, dependencies=[Depends(require_permissions(["ue.read"]))])
def get_ue(ue_id: int):
    try: return svc.get_ue(ue_id)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))

@router.post("/", response_model=UEOut, status_code=201, dependencies=[Depends(require_permissions(["ue.write"]))])
def create_ue(payload: UECreateIn):
    try: return svc.create_ue(payload)
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))

@router.put("/{ue_id}", response_model=UEOut, dependencies=[Depends(require_permissions(["ue.write"]))])
def update_ue(ue_id: int, payload: UEUpdateIn):
    try: return svc.update_ue(ue_id, payload)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{ue_id}", status_code=204, dependencies=[Depends(require_permissions(["ue.write"]))])
def delete_ue(ue_id: int):
    try: svc.delete_ue(ue_id); return
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
