from typing import Optional
from api.controller import ue_controller as uc

def _row(r):
    return {"id": r[0], "program_id": r[1], "code": r[2], "title": r[3],
            "year_no": r[4], "sem_no": r[5], "ects": r[6],
            "description": r[7], "created_at": r[8]}

def create_ue(payload):
    r = uc.create_ue(payload.program_id, payload.code, payload.title, payload.year_no, payload.sem_no, payload.ects, payload.description)
    return _row(r)

def update_ue(ue_id: int, payload):
    r = uc.update_ue(ue_id, payload.title, payload.year_no, payload.sem_no, payload.ects, payload.description)
    return _row(r)

def get_ue(ue_id: int):
    r = uc.get_ue(ue_id)
    if not r: raise ValueError("UE introuvable")
    return _row(r)

def list_ue(limit: int, offset: int, q: Optional[str], program_id: Optional[int], year_no: Optional[int], sem_no: Optional[int]):
    rows, total = uc.list_ue(limit, offset, q, program_id, year_no, sem_no)
    return {"items": [_row(r) for r in rows], "limit": limit, "offset": offset, "total": int(total)}

def delete_ue(ue_id: int):
    uc.delete_ue(ue_id); return {"message": "UE supprimée"}
