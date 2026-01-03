from fastapi import APIRouter, Depends, HTTPException
from utils.auth import require_permissions
from schema.progression import LessonProgressIn, LessonProgressOut
from api.services import progression_service as svc


router = APIRouter(prefix="/lessons", tags=["progress"])

@router.post("/{lesson_id}/progress", response_model=LessonProgressOut)
def set_progress(
    lesson_id: int,
    payload: LessonProgressIn,
    user_id: int = Depends(require_permissions(["lesson.write"]))
):
    try:
        return svc.set_progress(user_id=user_id, lesson_id=lesson_id, status=payload.status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{lesson_id}/progress", response_model=LessonProgressOut)
def get_progress(
    lesson_id: int,
    user_id: int = Depends(require_permissions(["lesson.read"]))
):
    out = svc.get_progress(user_id=user_id, lesson_id=lesson_id)
    if not out:
        raise HTTPException(status_code=404, detail="Aucune progression")
    return out