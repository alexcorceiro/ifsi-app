from fastapi import HTTPException
from database.connection import get_db_connection, release_db_connection
from api.services.service_revision.revision_srs_service import RevisionSrsService
from schema.revision_schema import FlashcardCreateIn, FlashcardUpdateIn, SrsReviewIn



async def create_flashcard(payload: FlashcardCreateIn):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        flashcard_id = service.create_flashcard(payload.model_dump())
        conn.commit()
        return {"id": flashcard_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

async def list_flashcards(lesson_id: int | None = None, note_id: int | None = None, tag: str | None = None, limit: int = 50, offset: int = 0):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        items = service.list_flashcards(lesson_id=lesson_id, note_id=note_id, tag=tag, limit=limit, offset=offset)
        return {"items": items, "limit": limit, "offset": offset}
    finally:
        release_db_connection(conn)

async def update_flashcard(flashcard_id: int, payload: FlashcardUpdateIn):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        updated = service.update_flashcard(flashcard_id, payload.model_dump(exclude_none=True))
        conn.commit()
        return updated
    except ValueError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

async def delete_flashcard(flashcard_id: int):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        ok = service.delete_flashcard(flashcard_id)
        conn.commit()
        return {"ok": ok}
    except ValueError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

async def srs_due(user_id: int, limit: int = 20):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        return service.due(user_id=user_id, limit=limit)
    finally:
        release_db_connection(conn)

async def srs_review(payload: SrsReviewIn):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        res = service.review(
            user_id=payload.user_id,
            flashcard_id=payload.flashcard_id,
            quality=payload.quality,
            meta=payload.meta,
        )
        conn.commit()
        return res
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

async def srs_stats(user_id: int):
    conn = get_db_connection()
    try:
        service = RevisionSrsService(conn)
        return service.stats(user_id=user_id)
    finally:
        release_db_connection(conn)
