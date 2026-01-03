from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import require_permissions
from api.services import lesson_service as svc
from schema.lesson import LessonCreateIn, LessonUpdate, LessonOut, LessonListOut

router = APIRouter(prefix="/lessons", tags=["lessons"])

@router.get("/", response_model=LessonListOut, dependencies=[Depends(require_permissions(["lesson.read"]))])
def list_lessons(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 q: Optional[str] = Query(None), course_id: Optional[int] = Query(None)):
    return svc.list_lessons(limit, offset, q, course_id)

@router.get("/{lesson_id}", response_model=LessonOut, dependencies=[Depends(require_permissions(["lesson.read"]))])
def get_lesson(lesson_id: int):
    try:
        return svc.get_lesson(lesson_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/", response_model=LessonOut, status_code=201, dependencies=[Depends(require_permissions(["lesson.write"]))])
def create_lesson(payload: LessonCreateIn):
    try:
        return svc.create_lesson(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{lesson_id}", response_model=LessonOut, dependencies=[Depends(require_permissions(["lesson.write"]))])
def update_lesson(lesson_id: int, payload: LessonUpdate):
    try:
        return svc.update_lesson(lesson_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{lesson_id}", status_code=204, dependencies=[Depends(require_permissions(["lesson.write"]))])
def delete_lesson(lesson_id: int):
    try:
        svc.delete_lesson(lesson_id)
        return
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))