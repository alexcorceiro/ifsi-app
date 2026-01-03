from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import require_permissions
from api.services import protocols_service as svc
from schema.protocols import (
    CategoryCreateIn, CategoryOut, ProtocolCreateIn, ProtocolUpdateIn, ProtocolOut,
    ProtocolVersionCreateIn, ProtocolVersionOut
)


router = APIRouter(prefix="/protocols", tags=["protocols"])

@router.post("/", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.write"]))])
def create_protocol(payload: ProtocolCreateIn):
    try:
        return svc.create_protocol(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/{protocol_id}", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.read"]))])
def update_protocol(protocol_id: int, payload: ProtocolUpdateIn):
    try:
        return svc.update_protocol(protocol_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/{protocol_id}", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.write"]))])
def get_protocol(protocol_id: int):
    try: 
        return svc.get_protocol(protocol_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/", dependencies=[Depends(require_permissions(["protocols.read"]))])
def list_protocols(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   q: Optional[str]=Query(None), category_id: Optional[int]=Query(None)):
    return svc.list_protocols(limit, offset, q, category_id)

@router.delete("/{protocol_id}", dependencies=[Depends(require_permissions(["protocols.write"]))])
def delete_protocol(protocol_id: int):
    try:
        return svc.delete_protocol(protocol_id)
    except ValueError as e: 
        raise HTTPException(status_code=404, detail=str(e))
    
@router.post("/{protocol_id}/versions",
             response_model=ProtocolVersionOut,
             dependencies=[Depends(require_permissions(["protocols.write"]))])
def create_version(protocol_id: int, payload: ProtocolVersionCreateIn):
    try:
        return svc.create_protocol_version(protocol_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{protocol_id}/versions",
            dependencies=[Depends(require_permissions(["protocols.read"]))])
def list_versions(protocol_id: int):
    return svc.list_protocol_versions(protocol_id)