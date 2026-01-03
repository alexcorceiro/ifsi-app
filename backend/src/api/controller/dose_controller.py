from fastapi import HTTPException, Query
from database.connection import get_db_connection
from core.dose_repo import DoseRepo
from schema.dose_schema import DoseCalculateIn, DoseCalculateOut, DoseCalculatuionUpdateIn
from api.services.service_dose.dose_service import DoseService


async def calculate(payload: DoseCalculateIn) -> DoseCalculateOut:
    conn = get_db_connection()
    try:
        service = DoseService(conn)
        res = service.calculate(payload)
        return DoseCalculateOut(
            calculation_id=res["calculation_id"],
            dose_result=res["dose_result"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {e}")
    finally:
        conn.close()

async def list_calculations(
    user_id: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            rows = DoseRepo.list_calculations(cur, user_id=user_id, limit=limit, offset=offset)
        return {"items": rows, "limit": limit, "offset": offset}
    finally:
        conn.close()

async def get_calculation(calc_id: int):
    conn = get_db_connection()
    try: 
        with conn.cursor() as cur:
            row = DoseRepo.get_calculation(cur, calc_id)
        if not row:
            raise HTTPException(status_code=404, detail="calculation not found")
        return row
    finally :
        conn.close()

    

async def update_calculation(calc_id: int, payload: DoseCalculatuionUpdateIn):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updated = DoseRepo.update_calculation(
                cur, calc_id, notes=payload.notes, context=payload.context
            )
            if not updated:
                with conn.cursor() as cur:
                    exists = DoseRepo.get_calculation(cur, calc_id)
                if not exists:
                    raise HTTPException(status_code=404, detail="calculation not found")
                raise HTTPException(status_code=400, detail="Aucun champ a mettre a jour ")
            conn.commit()
            return updated
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {e}")
    finally:
        conn.close()

async def delete_calculation(calc_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            ok = DoseRepo.delete_calculation(cur, calc_id)
        if not ok:
            raise HTTPException(detail_status=404, detail="calculation not found")
        conn.commit()
        return  {"status": "DELETED", "id": calc_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail="Erreur serveur: {e}")
    finally: 
        conn.close()