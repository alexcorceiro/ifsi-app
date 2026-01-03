from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import require_permissions
from api.services import program_service as svc
from schema.program import ProgramCreateIn, ProgramUpdateIn, ProgramOut, ProgramListOut

router = APIRouter(prefix="/programs", tags=["programs"])

@router.get("/", response_model=ProgramListOut, dependencies=[Depends(require_permissions(["programs.read"]))])
def list_programs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), q: Optional[str]=Query(None)):
    return svc.list_programs(limit, offset, q)

@router.get("/{pid}", response_model=ProgramOut, dependencies=[Depends(require_permissions(["programs.read"]))])
def get_program(pid: int):
    try: return svc.get_program(pid)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))

@router.post("/", response_model=ProgramOut, status_code=201, dependencies=[Depends(require_permissions(["programs.write"]))])
def create_program(payload: ProgramCreateIn):
    try: return svc.create_program(payload)
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))

@router.put("/{pid}", response_model=ProgramOut, dependencies=[Depends(require_permissions(["programs.write"]))])
def update_program(pid: int, payload: ProgramUpdateIn):
    try: return svc.update_program(pid, payload)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{pid}", status_code=204, dependencies=[Depends(require_permissions(["programs.write"]))])
def delete_program(pid: int):
    try: svc.delete_program(pid); return
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
