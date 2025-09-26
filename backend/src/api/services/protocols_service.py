from typing import Optional, Tuple, List, Dict
from api.controller import protocols_controller as repo
from schema.protocols import (ProtocolCreate, ProtocolUpdate, ProtocolNewVersion)

def create_protocol(payload: ProtocolCreate, user_id: int) -> Dict:
    if repo.get_by_code(payload.code):
        raise ValueError("ce code existe deja")
    data = payload.model_dump()
    data["created_by"] = user_id
    proto = repo.insert_protocol(data)

    if payload.body_md:
        v = repo.insert_version(proto["id"], payload.body_md, None, payload.publish_now)
        proto["latest_version"] = v
    else:
        proto["latest_version"] = repo.get_latest_version(proto["id"])
    return proto

def get_protocol(pid: int) -> Dict:
    p = repo.get_by_id(pid)
    if not p:
        raise ValueError("protocole introuvable")
    p["latest_version"] = repo.get_latest_version(pid)
    return p

def list_protocols(q: Optional[str], category_id: Optional[int],
                   published: Optional[bool], limit: int, offset: int) -> Tuple[int, List[Dict]]:
    total, items = repo.list_protocols(q, category_id, published, limit, offset)
    out = []
    for it in items:
        it["latest_version"] = repo.get_latest_version(it["id"])
        out.append(it)
    return total, items

def update_protocol(pid: int, payload: ProtocolUpdate) -> Dict:
    data = payload.model_dump(exclude_unset=True)
    updated = repo.update_protocol(pid, data)
    if not updated:
        raise ValueError("Protocol introuvable")
    updated["latest_version"] = repo.get_latest_version(pid)
    return updated

def create_new_version(pid: int, payload: ProtocolNewVersion) -> Dict:
    if not repo.get_by_id(pid):
        raise ValueError("Protocol introuvable ")
    v = repo.insert_protocol(pid, payload.body_md, payload.changelog, payload.publish_now)
    p = repo.get_by_id(pid)
    p["latest_version"] = v
    return p

def delete_protocol(pid: int) -> None:
    if not repo.delete_protocol(pid):
        raise ValueError("protocole introuvable")