from fastapi import HTTPException,  Query
from database.connection import get_db_connection
from schema.case_schema import CaseStartIn, StepAnswerIn
from api.services.service_training.case_engine import CaseEngineService
from core.case_repo import CaseRepo


async def list_cases(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            rows = CaseRepo.list_cases(cur, limit=limit, offset=offset)
        return{"items": rows, "limit": limit, "offset": offset}
    finally:
        conn.close()

async def get_case(case_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            row = CaseRepo.get_case(cur, case_id)
        if not row:
            raise HTTPException(status_code=404, detail="case not found")
        return row
    finally: 
        conn.close()

async def start_case(case_id: int, payload: CaseStartIn):
    conn = get_db_connection()
    try:
        service = CaseEngineService(conn)
        return service.start_case(case_id=case_id, user_id=payload.user_id)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
async def get_attempt_state(attempt_id: int):
    conn = get_db_connection()
    try:
        service = CaseEngineService(conn)
        return service.get_attempt_state(attempt_id=attempt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {e}")
    finally:
        conn.close()


async def answer_step(attempt_id: int, step_id: int, payload: StepAnswerIn):
    conn = get_db_connection()
    try:
        service = CaseEngineService(conn)
        return service.answer_step(
            attempt_id=attempt_id,
            step_id=step_id,
            payload=payload.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {e}")
    finally:
        conn.close()