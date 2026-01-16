from __future__   import annotations
from typing import Any, Dict, List, Optional
from psycopg2.extras import Json
import json

def _row_id(row) -> int:
    if row is None:
        raise ValueError("aucune ligne retourner par RETURNING")
    return row["id"] if isinstance(row, dict) else row[0]

def _fetchone_dict(cur):
    row = cur.fetchone()
    if row is None:   # ✅ CORRECTION
        return None
    if isinstance(row, dict):
        return row
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return dict(zip(cols, row))

def _fetchall_dict(cur):
    rows = cur.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]

def _row_to_dict(cur, row) -> Dict[str, Any]:
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))


def _row_id_from_returning(row) -> int:

    if row is None:
        raise ValueError("RETURNING id a renvoyé None")
    if isinstance(row, dict):
        return int(row["id"])
    return int(row[0])

class QuizRepo:
    @staticmethod
    def create_quiz(cur, payload: Dict[str, Any]) -> int:
       cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='learning'
          AND table_name='quizzes'
          AND column_name='attempts_limit'
        """)
       has_attempts_limit = cur.fetchone() is not None

       if has_attempts_limit:
            cur.execute(
                """
                INSERT INTO learning.quizzes
                (titre, tags, niveau, is_published, mode, duration_sec, pass_mark,
                shuffle_items, shuffle_options, attempts_limit, created_by)
                VALUES
                (%s, %s::text[], %s, %s, %s, %s, %s,
                %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["titre"],
                    payload.get("tags", []),
                    payload.get("niveau"),
                    payload.get("is_published", False),
                    payload.get("mode", "entrainement"),
                    payload.get("duration_sec"),
                    payload.get("pass_mark"),
                    payload.get("shuffle_items", True),
                    payload.get("shuffle_options", True),
                    payload.get("attempts_limit"),
                    payload.get("created_by"),
                ),
            )
       else:
            cur.execute(
                """
                INSERT INTO learning.quizzes
                (titre, tags, niveau, is_published, mode, duration_sec, pass_mark,
                shuffle_items, shuffle_options, created_by)
                VALUES
                (%s, %s::text[], %s, %s, %s, %s, %s,
                %s, %s, %s)
                RETURNING id
                """,
                (
                    payload["titre"],
                    payload.get("tags", []),
                    payload.get("niveau"),
                    payload.get("is_published", False),
                    payload.get("mode", "entrainement"),
                    payload.get("duration_sec"),
                    payload.get("pass_mark"),
                    payload.get("shuffle_items", True),
                    payload.get("shuffle_options", True),
                    payload.get("created_by"),
                ),
            )

       return _row_id(cur.fetchone())
    
    @staticmethod
    def get_quiz(cur, quiz_id: int) -> Optional[Dict[str, Any]]:
        cur.execute(
            """
            SELECT id, titre, tags, niveau, is_published, mode, duration_sec, pass_mark,
                   shuffle_items, shuffle_options, attempts_limit, created_by, created_at, updated_at
            FROM learning.quizzes
            WHERE id = %s
            """,
            (quiz_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return row if isinstance(row, dict) else _row_to_dict(cur, row)
    
    @staticmethod
    def list_quizzes(
        cur,
        *,
        tag: Optional[str],
        mode: Optional[str],
        is_published: Optional[bool],
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        where = []
        params: List[Any] = []

        if tag:
            where.append("%s = ANY(tags)")
            params.append(tag)
        if mode:
            where.append("mode=%s")
            params.append(mode)
        if is_published is not None:
            where.append("is_published=%s")
            params.append(is_published)

        wsql = ("WHERE " + " AND ".join(where)) if where else ""
        params.extend([limit, offset])

        cur.execute(
            f"""
            SELECT *
            FROM learning.quizzes
            {wsql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        return _fetchall_dict(cur)
 
    @staticmethod
    def update_quiz(cur, quiz_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        params: List[Any] = []

        for k in (
            "titre",
            "tags",
            "niveau",
            "is_published",
            "mode",
            "duration_sec",
            "pass_mark",
            "shuffle_items",
            "shuffle_options",
            "attempts_limit",
        ):
            if k in payload and payload[k] is not None:
                if k == "tags":
                    fields.append("tags=%s::text[]")
                    params.append(payload[k])
                else:
                    fields.append(f"{k}=%s")
                    params.append(payload[k])

        if not fields:
            return None

        params.append(quiz_id)
        cur.execute(
            f"""
            UPDATE learning.quizzes
            SET {", ".join(fields)}
            WHERE id=%s
            RETURNING *
            """,
            tuple(params),
        )
        return _fetchone_dict(cur)

    @staticmethod
    def delete_quiz(cur, quiz_id: int) -> bool:
        cur.execute("DELETE FROM learning.quizzes WHERE id=%s RETURNING id", (quiz_id,))
        return bool(cur.fetchone())
    
    @staticmethod
    def create_item(cur, quiz_id: int, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO learning.quiz_items
              (quiz_id, type, question_md, options_json, bonne_reponse,
               explication_md, ordre, difficulty, tags)
            VALUES
              (%s, %s, %s,
               %s::jsonb, %s::jsonb,
               %s, %s, %s, %s::text[])
            RETURNING id
            """,
            (
                quiz_id,
                payload.get("type", "qcm"),
                payload["question_md"],
                json.dumps(payload.get("options_json")) if payload.get("options_json") is not None else None,
                json.dumps(payload.get("bonne_reponse")) if payload.get("bonne_reponse") is not None else None,
                payload.get("explication_md"),
                payload.get("ordre", 0),
                payload.get("difficulty"),
                payload.get("tags", []),
            ),
        )
        return _row_id(cur.fetchone())

    @staticmethod
    def get_item(cur, item_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM learning.quiz_items WHERE id=%s", (item_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return row if isinstance(row, dict) else _row_to_dict(cur, row)

    @staticmethod
    def list_items(cur, quiz_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT *
            FROM learning.quiz_items
            WHERE quiz_id=%s
            ORDER BY ordre ASC, id ASC
            """,
            (quiz_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return rows
        return [_row_to_dict(cur, r) for r in rows]

    # -------------------------
    # Attempts / Answers
    # -------------------------
    @staticmethod
    def count_attempts_for_user(cur, quiz_id: int, user_id: int) -> int:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM learning.quiz_attempts
            WHERE quiz_id=%s AND user_id=%s
            """,
            (quiz_id, user_id),
        )
        row = cur.fetchone()
        return int(row["count"] if isinstance(row, dict) and "count" in row else row[0])

    @staticmethod
    def create_attempt(cur, *, quiz_id: int, user_id: int, meta: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO learning.quiz_attempts (quiz_id, user_id, meta)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (quiz_id, user_id, Json(meta or {})),  # ✅ dict -> JSON adapté
        )
        return _row_id_from_returning(cur.fetchone())

    @staticmethod
    def get_attempt(cur, attempt_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM learning.quiz_attempts WHERE id=%s", (attempt_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return row if isinstance(row, dict) else _row_to_dict(cur, row)

    @staticmethod
    def upsert_answer(
        cur,
        *,
        attempt_id: int,
        item_id: int,
        answers_json: Dict[str, Any],
        is_correct: Optional[bool],
    ) -> Dict[str, Any]:
        cur.execute(
            """
            INSERT INTO learning.quiz_answers
              (attempt_id, item_id, answers_json, is_correct)
            VALUES
              (%s, %s, %s::jsonb, %s)
            ON CONFLICT (attempt_id, item_id)
            DO UPDATE SET
              answers_json=EXCLUDED.answers_json,
              is_correct=EXCLUDED.is_correct,
              responded_at=NOW()
            RETURNING *
            """,
            (attempt_id, item_id, json.dumps(answers_json or {}), is_correct),
        )
        row = _fetchone_dict(cur)
        if row is None:
            raise ValueError("upsert_answer: aucune ligne retournée")
        return row

    @staticmethod
    def list_answers_for_attempt(cur, attempt_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT *
            FROM learning.quiz_answers
            WHERE attempt_id=%s
            ORDER BY responded_at ASC, id ASC
            """,
            (attempt_id,),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def finish_attempt(cur, *, attempt_id: int, score_raw: int, score_max: int) -> Dict[str, Any]:
        cur.execute(
            """
            UPDATE learning.quiz_attempts
            SET finished_at=NOW(), score_raw=%s, score_max=%s
            WHERE id=%s
            RETURNING *
            """,
            (score_raw, score_max, attempt_id),
        )
        row = _fetchone_dict(cur)
        if row is None:
            raise ValueError("finish_attempt: attempt not found")
        return row