from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import Optional, List, Dict, Any
from schema.protocols import ( ProtocolCreate,ProtocolUpdate, ProtocolNewVersion, ProtocolOut, ProtocolListOut)
from api.services import protocols_service as svc
from utils.auth import require_permissions, require_bearer

router = APIRouter(prefix="/protocols", tags=["protocols"])

@router.get("", response_model=ProtocolListOut, dependencies=[Depends(require_permissions(["protocols.read"]))])
def list_protocols(
   q: Optional[str] = Query(default=None, description="Recherche FTS sur title, summary, code, body"),
   category_id: Optional[int] = Query(default=None),
   published: Optional[bool] = Query(default=None),
   limit: int = Query(default=20, ge=1, le=100),
   offset: int = Query(default=0, ge=0)
):
    total, items = svc.list_protocols(q, category_id, published, limit, offset)
    return {"total": total, "items": items, "limit": limit, "offset": offset}


@router.get("/{protocol_id}", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.read"]))])
def get_protocol(protocol_id: int ):
    try: 
        return svc.get_protocol(protocol_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("", response_model=ProtocolOut, status_code=201, dependencies=[Depends(require_permissions(["protocols.write"]))])
def create_protocol(payload: ProtocolCreate, user= Depends(require_bearer)):
    try:
        user_id = int(user["user_id"])
        return svc.create_protocol(payload, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{protocol_id}", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.write"]))])
def update_protocol(protocol_id: int, payload: ProtocolUpdate):
    try: 
        return svc.update_protocol(protocol_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{protocol_id}/versions", response_model=ProtocolOut, dependencies=[Depends(require_permissions(["protocols.write"]))])
def add_version(protocol_id: int, payload: ProtocolNewVersion):
    try: 
        return svc.create_new_version(protocol_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/{protocol_id}", status_code=204, dependencies=[Depends(require_permissions(["protocols.write"]))])
def remove_protocol(protocol_id: int): 
    try:
        svc.delete_protocol(protocol_id)
    except ValueError as e: 
        raise HTTPException(status_code=404, detail=str(e))
