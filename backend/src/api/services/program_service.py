from typing import Optional
from api.controller import program_controller as pc

def _row(r): return {"id": r[0], "code": r[1], "label": r[2], "ects_total": r[3], "created_at": r[4]}

def create_program(payload):
    return _row(pc.create_program(payload.code, payload.label, payload.ects_total))

def update_program(pid: int, payload):
    return _row(pc.update_program(pid, payload.label, payload.ects_total))

def get_program(pid: int):
    r = pc.get_program(pid)
    if not r: raise ValueError("Programme introuvable")
    return _row(r)

def list_programs(limit: int, offset: int, q: Optional[str]):
    rows, total = pc.get_list_programs(limit, offset, q)
    return {"items": [_row(r) for r in rows], "limit": limit, "offset": offset, "total": int(total)}

def delete_program(pid: int):
    pc.delete_program(pid); return {"message": "Programme supprimé"}
