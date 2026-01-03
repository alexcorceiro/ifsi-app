from fastapi import HTTPException, Query
from database.connection import get_db_connection
from core.training_repo import TrainingRepo
from api.services.service_training.generator import TrainingGeneratorService
from api.services.service_training.corrector import TrainingCorrectorService
from schema.training_schema import ExerciseCreateIn, AttemptCreateIn

async def create_exercise(payload: ExerciseCreateIn):
    conn = get_db_connection()
    try:
        service = TrainingGeneratorService(conn)
        ex_id = service.create_exercise(payload.model_dump())
        return {"id": ex_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

async def list_exercises(
    exercise_type: str | None = None,
    difficulty: int | None = None,
    tag: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            rows = TrainingRepo.list_exercises(
                cur,
                exercise_type=exercise_type,
                difficulty=difficulty,
                tag=tag,
                limit=limit,
                offset=offset,
            )
        return {"items": rows, "limit": limit, "offset": offset}
    finally:
        conn.close()

async def get_exercise(exercise_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            row = TrainingRepo.get_exercise(cur, exercise_id)
        if not row:
            raise HTTPException(status_code=404, detail="exercise not found")
        return row
    finally:
        conn.close()

async def submit_attempt(exercise_id: int, payload: AttemptCreateIn):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            ex = TrainingRepo.get_exercise(cur, exercise_id)
        if not ex:
            raise HTTPException(status_code=404, detail="exercise not found")

        service = TrainingCorrectorService(conn)
        res = service.submit_attempt(exercise=ex, attempt_payload=payload.model_dump())
        return res
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

async def list_attempts(
    user_id: int | None = None,
    exercise_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            rows = TrainingRepo.list_attempts(
                cur,
                user_id=user_id,
                exercise_id=exercise_id,
                limit=limit,
                offset=offset,
            )
        return {"items": rows, "limit": limit, "offset": offset}
    finally:
        conn.close()

async def get_attempt(attempt_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            att = TrainingRepo.get_attempt(cur, attempt_id)
            if not att:
                raise HTTPException(status_code=404, detail="attempt not found")
            fb = TrainingRepo.list_attempt_feedback(cur, attempt_id)
        return {"attempt": att, "feedback_items": fb}
    finally:
        conn.close()
