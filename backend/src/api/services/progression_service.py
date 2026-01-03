from api.controller import progression_controller as pc

def set_progress(user_id: int, lesson_id: int, status: str):
    r = pc.upsert_progress(user_id, lesson_id, status)
    return {"user_id": r[0], "lesson_id":r[1], "status": r[2], "updated_at": r[3]}

def get_progress(user_id: int, lesson_id: int):
    r = pc.get_progress(user_id, lesson_id)
    if not r: return None
    return  {"user_id": r[0], "lesson_id": r[1], "status": r[2], "updated_at": r[3]}