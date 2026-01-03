from typing import Optional
from api.controller import protocols_controller as pc
from schema.protocols import ProtocolCreateIn, ProtocolUpdateIn, ProtocolVersionCreateIn, ProtocolVersionOut, ProtocolOut

def _protocol_row(r):
    return {
        "id": r[0], "category_id": r[1], "code": r[2], "title": r[3],
        "summary": r[4], "tags": r[5], "is_published": r[6],
        "created_at": r[7], "updated_at": r[8]
    }


def create_protocol(payload: ProtocolCreateIn):
    r = pc.create_protocol(payload.category_id, payload.code, payload.title, payload.summary,
                           payload.tags, payload.is_published, payload.external_url)
    return _protocol_row(r)

def update_protocol(protocol_id: int, payload: ProtocolUpdateIn):
    r = pc.update_protocol(protocol_id, payload.category_id, payload.title, payload.summary,
                           payload.tags, payload.is_published, payload.external_url)
    return _protocol_row(r)

def get_protocol(protocol_id: int):
    r = pc.get_protocol(protocol_id)
    if not r: raise ValueError("Protocol introuvable")
    return _protocol_row(r)

def list_protocols(limit: int, offset: int, q: Optional[str], category_id: Optional[int]):
    rows, total = pc.list_protocols(limit, offset, q, category_id)
    items = [_protocol_row(r) for r in rows]
    return {"items": items, "limit": limit, "offset": offset, "total": int(total)}

def create_protocol_version(protocol_id: int, payload: ProtocolVersionCreateIn):
    r = pc.create_protocol_version(protocol_id, payload.body_md, payload.changelog, payload.publish)
    return {"id": r[0], "protocol_id": r[1], "version": r[2], "body_md": r[3], "changelog": r[4], "published_at": r[5], "created_at": r[6]}

def list_protocol_versions(protocol_id: int):
    rows = pc.list_protocol_versions(protocol_id)
    return [{"id": r[0], "protocol_id": r[1], "version": r[2], "body_md": r[3], "changelog": r[4], "published_at": r[5], "created_at": r[6]} for r in rows]


def delete_protocol(protocol_id: int):
    pc.delete_protocol(protocol_id)
    return {"message": "Protocol supprime"}

