from __future__ import annotations
from typing import Any, Dict, List, Optional
from psycopg2.extras import Json


def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
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
        raise ValueError("RETURNING id vide")
    return int(row["id"]) if isinstance(row, dict) else int(row[0])

class RevisionSrsRepo:

    @staticmethod
    def create_flashcard(cur, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO revision.flashcards (note_id, lesson_id, front_md, back_md, tags)
            VALUES (%s, %s, %s, %s, %s::text[])
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
    def get_flashcard(cur, flashcard_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM revision.flashcards WHERE id=%s", (flashcard_id,))
        return _fetchone_dict(cur)

    @staticmethod
    def list_flashcards(
        cur,
        *,
        lesson_id: Optional[int],
        note_id: Optional[int],
        tag: Optional[str],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        where = []
        params: List[Any] = []

        if lesson_id is not None:
            where.append("lesson_id=%s")
            params.append(lesson_id)

        if note_id is not None:
            where.append("note_id=%s")
            params.append(note_id)

        if tag:
            where.append("%s = ANY(tags)")
            params.append(tag)

        wsql = "WHERE " + " AND ".join(where) if where else ""
        params.extend([limit, offset])

        # ta table flashcards a created_at (pas forcément updated_at)
        cur.execute(
            f"""
            SELECT *
            FROM revision.flashcards
            {wsql}
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def update_flashcard(cur, flashcard_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []

        for k in ("front_md", "back_md", "lesson_id", "note_id", "tags"):
            if k in payload and payload[k] is not None:
                if k == "tags":
                    fields.append("tags=%s::text[]")
                    params.append(payload[k])
                else:
                    fields.append(f"{k}=%s")
                    params.append(payload[k])

        if not fields:
            return None

        params.append(flashcard_id)
        cur.execute(
            f"""
            UPDATE revision.flashcards
            SET {", ".join(fields)}
            WHERE id=%s
            RETURNING *
            """,
            tuple(params),
        )
        return _fetchone_dict(cur)

    @staticmethod
    def delete_flashcard(cur, flashcard_id: int) -> bool:
        cur.execute("DELETE FROM revision.flashcards WHERE id=%s RETURNING id", (flashcard_id,))
        return cur.fetchone() is not None
    
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
    def upsert_schedule(
        cur,
        *,
        user_id: int,
        flashcard_id: int,
        interval_days: int,
        ease_factor: float,
        repetitions: int,
        due_at_iso: str,
    ) -> Dict[str, Any]:
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
            (user_id, flashcard_id, interval_days, ease_factor, repetitions, due_at_iso),
        )
        row = _fetchone_dict(cur)
        if row is None:
            raise ValueError("upsert_schedule: aucune ligne retournée")
        return row

    @staticmethod
    def insert_review(cur, user_id: int, flashcard_id: int, quality: int, meta: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO revision.srs_reviews (user_id, flashcard_id, quality, meta)
            VALUES (%s, %s, %s, %s::jsonb)
            RETURNING id
            """,
            (user_id, flashcard_id, quality, Json(meta or {})),
        )
        return _row_id(cur.fetchone())

    @staticmethod
    def list_due(cur, user_id: int, limit: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT
              f.*,
              s.interval_days, s.ease_factor, s.repetitions, s.due_at
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
    def stats_7d(cur, user_id: int) -> Dict[str, Any]:
        cur.execute(
            """
            SELECT
              COALESCE(COUNT(*), 0) AS reviews_7d,
              COALESCE(AVG(quality), 0) AS avg_quality_7d
            FROM revision.srs_reviews
            WHERE user_id=%s AND reviewed_at >= NOW() - INTERVAL '7 days'
            """,
            (user_id,),
        )
        row = _fetchone_dict(cur) or {}

        cur.execute(
            """
            SELECT COALESCE(COUNT(*), 0) AS due_now
            FROM revision.srs_schedules
            WHERE user_id=%s AND due_at <= NOW()
            """,
            (user_id,),
        )
        due = _fetchone_dict(cur) or {}

        return {
            "user_id": user_id,
            "due_now": int(due.get("due_now", 0)),
            "reviews_7d": int(row.get("reviews_7d", 0)),
            "avg_quality_7d": float(row.get("avg_quality_7d", 0)),
        }