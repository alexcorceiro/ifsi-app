from __future__ import annotations
from typing import Any, Dict, List, Optional
from psycopg2.extras import Json



def _fetchone_dict(cur):
    row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return dict(zip(cols, row))

def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def _row_id(row) -> int:
    if row is None:
        raise ValueError("RETURNING a renvoyé None")
    return int(row["id"]) if isinstance(row, dict) else int(row[0])



class RevisionRepo: 


    @staticmethod
    def create_sheet(cur, payload: dict) -> int:
        cur.execute(
            """
            INSERT INTO revision.revision_sheets
              (course_id, version_id, target_type, target_id, title, status, content_md)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload.get("course_id"),
                payload.get("version_id"),
                payload.get("target_type"),
                payload.get("target_id"),
                payload["title"],
                payload.get("status", "DRAFT"),
                payload.get("content_md"),
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError("create_sheet: RETURNING id vide")
        return row["id"] if isinstance(row, dict) else row[0]
    
    @staticmethod
    def get_sheet(cur, sheet_id: int):
        cur.execute(
            "SELECT * FROM revision.revision_sheets WHERE id=%s",
            (sheet_id,),
        )
        return _fetchone_dict(cur)
    
    @staticmethod
    def list_sheets(
        cur,
        *,
        course_id: Optional[int] = None,
        version_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        where, params = [], []

        if course_id is not None:
            where.append("course_id=%s")
            params.append(course_id)
        if version_id is not None:
            where.append("version_id=%s")
            params.append(version_id)
        if target_type is not None:
            where.append("target_type")
            params.append(target_type)
        if target_id is not None:
            where.append("targer_id")
            params.append(target_id)
        if status is not None:
            where.append("status=%s")
            params.append(status)

        wsql = ("WHERE" + "AND".join(where)) if where else ""
        params.extend([limit, offset])

        cur.execute(
                f"""
                SELECT *
                FROM revision.revision_sheets
                {wsql}
                ORDER BY updated_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params),
            )

        return _fetchall_dict(cur)
    
    @staticmethod
    def update_sheet(cur, sheet_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields: List[str] = []
        params: List[Any] = []

        # champs autorisés
        for k in ("title", "status", "content_md", "course_id", "version_id", "target_type", "target_id"):
            if k in payload and payload[k] is not None:
                fields.append(f"{k}=%s")
                params.append(payload[k])

        if not fields:
            return None

        params.append(sheet_id)

        # ✅ IMPORTANT: "SET " + " , ".join(...) avec espaces
        sql = f"""
            UPDATE revision.revision_sheets
            SET {", ".join(fields)}
            WHERE id=%s
            RETURNING *
        """

        cur.execute(sql, tuple(params))
        return _fetchone_dict(cur)
    
    @staticmethod
    def delete_sheet(cur, sheet_id: int) -> bool:
        cur.execute("DELETE FROM revision.revision_sheets WHERE id=%s RETURNING id",(sheet_id,))
        return cur.fetchone() is not None
    
    def create_item(cur, payload: Dict[str, Any]) -> int:
        cur.execute("""
            INSERT INTO revision.revision_sheet_items
              (sheet_id, item_type, position, title, body_md, source_id, page_start, page_end)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload["sheet_id"],
                payload.get("item_type", "BULLET"),
                payload.get("position", 1),
                payload.get("title"),
                payload["body_md"],
                payload.get("source_id"),
                payload.get("page_start"),
                payload.get("page_end"),
            ),
        )
        return _row_id(cur.fetchone())
    @staticmethod
    def list_items(cur, sheet_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT *
            FROM revision.revision_sheet_items
            WHERE sheet_id=%s
            ORDER BY position ASC, id ASC
            """,
            (sheet_id,),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def delete_item(cur, item_id: int) -> bool:
        cur.execute("DELETE FROM revision.revision_sheet_items WHERE id=%s RETURNING id", (item_id,))
        return cur.fetchone() is not None
    
    @staticmethod
    def list_items(cur, sheet_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT *
            FROM revision.revision_sheet_items
            WHERE sheet_id=%s
            ORDER BY position ASC, id ASC
            """,
            (sheet_id,),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def delete_item(cur, item_id: int) -> bool:
        cur.execute("DELETE FROM revision.revision_sheet_items WHERE id=%s RETURNING id", (item_id,))
        return cur.fetchone() is not None
    
    @staticmethod
    def create_note(cur, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO revision.notes
              (owner_id, ue_id, lesson_id, title, content_md, is_ai_generated, sources)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload.get("owner_id"),
                payload.get("ue_id"),
                payload.get("lesson_id"),
                payload["title"],
                payload["content_md"],
                bool(payload.get("is_ai_generated", False)),
                Json(payload.get("sources", [])),
            ),
        )
        return _row_id(cur.fetchone())
    
    @staticmethod
    def create_flashcard(cur, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO revision.flashcards
              (note_id, lesson_id, front_md, back_md, tags)
            VALUES
              (%s, %s, %s, %s, %s::text[])
            RETURNING id
            """,
            (
                payload.get("note_id"),
                payload.get("lesson_id"),
                payload["front_md"],
                payload["back_md"],
                payload.get("tags", []),
            ),
        )
        return _row_id(cur.fetchone())
    
    @staticmethod
    def get_schedule(cur, user_id: int, flashcard_id: int) -> Optional[Dict[str, Any]]:
        cur.execute(
            """
            SELECT *
            FROM revision.srs_schedules
            WHERE user_id=%s AND flashcard_id=%s
            """,
            (user_id, flashcard_id),
        )
        return _fetchone_dict(cur)

    @staticmethod
    def upsert_schedule(cur, payload: Dict[str, Any]) -> Dict[str, Any]:
        cur.execute(
            """
            INSERT INTO revision.srs_schedules
              (user_id, flashcard_id, interval_days, ease_factor, repetitions, due_at)
            VALUES
              (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, flashcard_id)
            DO UPDATE SET
              interval_days=EXCLUDED.interval_days,
              ease_factor=EXCLUDED.ease_factor,
              repetitions=EXCLUDED.repetitions,
              due_at=EXCLUDED.due_at,
              updated_at=NOW()
            RETURNING *
            """,
            (
                payload["user_id"],
                payload["flashcard_id"],
                payload["interval_days"],
                payload["ease_factor"],
                payload["repetitions"],
                payload["due_at"],
            ),
        )
        row = _fetchone_dict(cur)
        if row is None:
            raise ValueError("schedule not upserted")
        return row

    @staticmethod
    def insert_review(cur, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO revision.srs_reviews (user_id, flashcard_id, quality, meta)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload["user_id"],
                payload["flashcard_id"],
                payload["quality"],
                Json(payload.get("meta", {})),
            ),
        )
        return _row_id(cur.fetchone())

    @staticmethod
    def list_due(cur, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT s.*, f.front_md, f.back_md, f.tags
            FROM revision.srs_schedules s
            JOIN revision.flashcards f ON f.id = s.flashcard_id
            WHERE s.user_id=%s AND s.due_at <= NOW()
            ORDER BY s.due_at ASC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return _fetchall_dict(cur)
    
    @staticmethod
    def create_asset(cur, payload: Dict[str, Any]) -> int:
        """
        Insère un asset (image) positionné sur une fiche.
        - sheet_id obligatoire
        - asset_type obligatoire (ex: 'IMAGE')
        - source_id OU file_url
        - anchor: 'PAGE' | 'ITEM' | 'ABSOLUTE'
        - anchor_item_id si anchor='ITEM'
        - meta stocké en JSONB
        """
        cur.execute(
            """
            INSERT INTO revision.sheet_assets
              (sheet_id, asset_type, source_id, file_url,
               anchor, anchor_item_id,
               page_no, x, y, w, h, z_index,
               caption_md, meta)
            VALUES
              (%s, %s, %s, %s,
               %s, %s,
               %s, %s, %s, %s, %s, %s,
               %s, %s)
            RETURNING id
            """,
            (
                payload["sheet_id"],
                payload.get("asset_type", "IMAGE"),
                payload.get("source_id"),
                payload.get("file_url"),
                payload.get("anchor", "PAGE"),
                payload.get("anchor_item_id"),
                payload.get("page_no", 1),
                payload.get("x", 0),
                payload.get("y", 0),
                payload.get("w", 100),
                payload.get("h", 100),
                payload.get("z_index", 0),
                payload.get("caption_md"),
                Json(payload.get("meta") or {}),
            ),
        )
        return _row_id(cur.fetchone())
    
    @staticmethod
    def list_assets(cur, sheet_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT
              id,
              sheet_id,
              asset_type,
              source_id,
              file_url,
              anchor,
              anchor_item_id,
              page_no,
              x, y, w, h,
              z_index,
              caption_md,
              meta,
              created_at
            FROM revision.sheet_assets
            WHERE sheet_id=%s
            ORDER BY page_no ASC, z_index ASC, id ASC
            """,
            (sheet_id,),
        )
        return _fetchall_dict(cur)
    
    @staticmethod
    def delete_asset(cur, asset_id: int) -> bool:
        cur.execute(
            """
            DELETE FROM revision.sheet_assets
            WHERE id=%s
            RETURNING id
            """,
            (asset_id,),
        )
        return cur.fetchone() is not None