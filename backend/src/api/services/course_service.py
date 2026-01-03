from typing import Optional
from api.controller import cours_controller as cc
from schema.courses import CourseCreateIn, CourseUpdateIn

def _row_to_dict(r):
    return {
        "id": r[0], "ue_id": r[1], "code": r[2], "title": r[3],
        "summary": r[4],                 # DB.description -> API.summary
        "order_no": r[5],
        "created_at": r[6], "updated_at": r[7]
    }

def create_course(payload: CourseCreateIn):
    r = cc.create_course(payload.ue_id, payload.code, payload.title, payload.summary, payload.order_no)
    return _row_to_dict(r)

def update_course(course_id: int, payload: CourseUpdateIn):
    r = cc.update_course(course_id, payload.ue_id, payload.title, payload.summary, payload.order_no)
    return _row_to_dict(r)

def get_course(course_id: int):
    r = cc.get_course(course_id)
    if not r: raise ValueError("Cours introuvable")
    return _row_to_dict(r)

def list_courses(limit: int, offset: int, q: Optional[str], ue_id: Optional[int]):
    rows, total = cc.list_courses(limit, offset, q, ue_id)
    return {"items": [_row_to_dict(r) for r in rows], "limit": limit, "offset": offset, "total": int(total)}

def delete_course(course_id: int):
    cc.delete_course(course_id)
    return {"message": "Cours supprimé"}
