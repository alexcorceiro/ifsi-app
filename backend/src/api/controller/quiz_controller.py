from __future__ import annotations
from fastapi import HTTPException, Query
from database.connection import get_db_connection , release_db_connection
from core.quiz_repo import QuizRepo
from api.services.service_quiz.quiz_service import QuizService

from schema.quiz_schema import (
    QuizCreateIn,
    QuizUpdateIn,
    QuizItemCreateIn,
    QuizAttemptStartIn,
    QuizAnswerIn,
)


async def create_quiz(payload: QuizCreateIn):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        quiz_id = service.create_quiz(payload.model_dump())
        conn.commit()
        return {"id": quiz_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))

async def list_quizzes(
    tag: str | None = None,
    mode: str | None = None,
    is_published: bool | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            rows = QuizRepo.list_quizzes(
                cur,
                tag=tag,
                mode=mode,
                is_published=is_published,
                limit=limit,
                offset=offset,
            )
        return {"items": rows, "limit": limit, "offset": offset}
    finally:
        release_db_connection(conn)

async def get_quiz(quiz_id: int):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        quiz = service.get_quiz(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="quiz not found")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)
    
async def update_quiz(quiz_id: int, payload: QuizUpdateIn):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        updated = service.update_quiz(quiz_id, payload.model_dump(exclude_unset=True))
        conn.commit()
        return updated
    except ValueError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)

async def delete_quiz(quiz_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            ok = QuizRepo.delete_quiz(cur, quiz_id)
        if not ok:
            conn.rollback()
            raise HTTPException(status_code=404, detail="quiz not found")
        conn.commit()
        return {"status": "DELETED", "id": quiz_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)

async def create_item(quiz_id: int, payload: QuizItemCreateIn):
    conn = get_db_connection()
    try: 
        service = QuizService(conn)
        item_id = service.create_item(quiz_id, payload.model_dump())
        conn.commit()
        return {"id": item_id}
    except Exception as e:
        conn.rollack()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)

async def list_items(quiz_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor as cur:
            quiz = QuizRepo.get_quiz(cur, quiz_id)
            if not quiz:
                raise HTTPException(status_code=404, detail="quiz not found")
            rows = QuizRepo.list_items(cur, quiz_id)
        return {"items": rows}
    finally:
        release_db_connection(conn)

async def start_attempt(quiz_id: int, payload: QuizAttemptStartIn):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        res = service.start_attempt(quiz_id, payload.user_id, payload.meta)
        conn.commit()
        return {
            "attempt": res.attempt,
            "item_order": res.item_order,
            "options_order": res.options_order,
            "items": res.items,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)


async def answer_item(attempt_id: int, item_id: int, payload: QuizAnswerIn):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        res = service.answer_item(attempt_id, item_id, payload.answers_json)
        conn.commit()
        return res
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)


async def finish_attempt(attempt_id: int):
    conn = get_db_connection()
    try:
        service = QuizService(conn)
        res = service.finish_attempt(attempt_id)
        conn.commit()
        return res
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)
