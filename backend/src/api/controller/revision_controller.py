from __future__ import  annotations
from fastapi import HTTPException, Query



from api.services.service_revision.revision_service import RevisionService
from schema.revision_schema import (
    RevisionSheetCreateIn,
    RevisionSheetUpdateIn,
    RevisionSheetItemCreateIn,
    SheetAssetCreateIn
)

from database.connection import get_db_connection, release_db_connection



async def create_sheet(payload: RevisionSheetCreateIn):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        sheet_id = service.create_sheet(payload.model_dump())
        conn.commit()
        return {"id": sheet_id}
    except ValueError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

async def list_sheets(
      course_id: int | None = None,
    version_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),   
):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        items = service.list_sheets(
            course_id=course_id,
            version_id=version_id,
            target_type=target_type,
            target_id=target_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return {"items": items, "limit": limit, "offset": offset}
    finally:
        release_db_connection(conn)

async def get_sheet(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        return service.get_sheet(sheet_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        release_db_connection(conn)


async def get_sheet_full(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        return service.get_sheet_full(sheet_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        release_db_connection(conn)



async def render_sheet(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        return service.render_sheet_blocks(sheet_id)

    except ValueError as e:
        # not found métier
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # erreur technique
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        release_db_connection(conn)

async def update_sheet(sheet_id: int, payload: RevisionSheetUpdateIn):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        updated = service.update_sheet(sheet_id, payload.model_dump(exclude_unset=True))
        conn.commit()
        return updated
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)


async def delete_sheet(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        service.delete_sheet(sheet_id)
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        # si not found => 404
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    finally:
        release_db_connection(conn)

async def add_item(payload: RevisionSheetItemCreateIn):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        item_id = service.add_item(payload.model_dump())
        conn.commit()
        return {"id": item_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)


async def list_items(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        items = service.list_items(sheet_id)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        release_db_connection(conn)


async def delete_item(item_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        service.delete_item(item_id)
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    finally:
        release_db_connection(conn)

async def add_asset(payload: SheetAssetCreateIn):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        asset_id = service.add_asset(payload.model_dump())
        conn.commit()
        return {"id": asset_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        release_db_connection(conn)


async def list_assets(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        assets = service.list_assets(sheet_id)
        return {"items": assets}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        release_db_connection(conn)


async def delete_asset(asset_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        service.delete_asset(asset_id)
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    finally:
        release_db_connection(conn)


async def render_sheet_pages(sheet_id: int):
    conn = get_db_connection()
    try:
        service = RevisionService(conn)
        return service.render_sheet_pages(sheet_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db_connection(conn)

        