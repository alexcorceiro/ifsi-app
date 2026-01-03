from typing import Optional
from api.controller import lesson_controller as lc
from schema.lesson import LessonCreateIn, LessonUpdate

def _row_to_dict(r):
    return {
        "id": r[0], "course_id": r[1], "code": r[2], "title": r[3],
        "summary": r[4], "body_md": r[5], "created_at": r[6], "updated_at": r[7]
    }

def create_lesson(payload: LessonCreateIn):
    r = lc.create_lesson(payload.course_id, payload.code, payload.title, payload.code, payload.body_md, payload.summary)
    return _row_to_dict(r)

def update_lesson(lesson_id: int, payload: LessonUpdate):
    r = lc.update_lesson(lesson_id, payload)
    return _row_to_dict(r)

def get_lesson(lesson_id: int):
    r = lc.get_lesson(lesson_id)
    if not r: raise ValueError("lecon introuvable ")
    return _row_to_dict(r)

def list_lessons(limit: int, offset: int, q: Optional[str], course_id: Optional[int]):
    rows, total = lc.get_list_lessons(limit, offset, q, course_id)
    items = [_row_to_dict(r) for r in rows ]
    return {"items": items, "limit": limit, "offset": offset, "total": int(total)}

def delete_lesson(lesson_id: int):
    lc.delete_lesson(lesson_id)
    return {"message": "Lecon supprimée "}
