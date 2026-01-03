# src/core/training_repo.py
from typing import Optional, List, Dict, Any
import json


def _row_id(row) -> int:
    """Compat dict-cursor ET tuple-cursor."""
    if row is None:
        raise ValueError("Aucune ligne retournée par RETURNING id")
    return row["id"] if isinstance(row, dict) else row[0]


def _fetchone_dict(cur):
    """
    Retourne une ligne en dict, quel que soit le type de cursor.
    - RealDictCursor => dict
    - Cursor classique => tuple, converti via cur.description
    """
    row = cur.fetchone()
    if row is None:
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


class TrainingRepo:
    @staticmethod
    def create_exercise(cur, payload: Dict[str, Any]) -> int:
        cur.execute(
            """
            INSERT INTO training.dose_exercises
              (title, statement_md, exercise_type, difficulty, tags,
               expected, solution_steps, created_by, source, metadata)
            VALUES
              (%s,%s,%s,%s,%s::text[],
               %s::jsonb,%s::jsonb,%s,%s,%s::jsonb)
            RETURNING id
            """,
            (
                payload["title"],
                payload["statement_md"],
                payload["exercise_type"],
                payload["difficulty"],
                payload.get("tags", []),
                json.dumps(payload.get("expected", {})),
                json.dumps(payload.get("solution_steps", [])),
                payload.get("created_by"),
                payload.get("source", "TEACHER"),
                json.dumps(payload.get("metadata", {})),
            ),
        )
        return _row_id(cur.fetchone())

    @staticmethod
    def get_exercise(cur, exercise_id: int):
        cur.execute("SELECT * FROM training.dose_exercises WHERE id=%s", (exercise_id,))
        return _fetchone_dict(cur)

    @staticmethod
    def list_exercises(
        cur,
        *,
        exercise_type: Optional[str],
        difficulty: Optional[int],
        tag: Optional[str],
        limit: int,
        offset: int,
    ):
        where = []
        params = []

        if exercise_type:
            where.append("exercise_type=%s")
            params.append(exercise_type)
        if difficulty:
            where.append("difficulty=%s")
            params.append(difficulty)
        if tag:
            where.append("%s = ANY(tags)")
            params.append(tag)

        sql = "SELECT * FROM training.dose_exercises"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(sql, tuple(params))
        return _fetchall_dict(cur)

    @staticmethod
    def create_attempt(
            cur,
            *,
            user_id: int,
            exercise_id: int,
            submitted_json: Dict[str, Any],
            submitted_value,
            submitted_unit,
            is_correct: bool,
            score: float,
            error_codes: List[str],
            ai_feedback_md: Optional[str],
            calculation_id: Optional[int],
            time_ms: Optional[int],
        ) -> int:
            cur.execute(
                """
                INSERT INTO training.dose_attempts
                (user_id, exercise_id, submitted_json,
                submitted_value, submitted_unit,
                is_correct, score, error_codes,
                ai_feedback_md, calculation_id, time_ms)
                VALUES
                (%s,%s,%s::jsonb,%s,%s,%s,%s,%s::text[],%s,%s,%s)
                RETURNING id
                """,
                (
                    user_id,
                    exercise_id,
                    json.dumps(submitted_json or {}),
                    submitted_value,
                    submitted_unit,
                    is_correct,
                    score,
                    error_codes or [],
                    ai_feedback_md,
                    calculation_id,
                    time_ms,
                ),
            )
            row = cur.fetchone()
            return row["id"] if isinstance(row, dict) else row[0]

    @staticmethod
    def insert_attempt_feedback(
        cur,
        *,
        attempt_id: int,
        code: str,
        severity: int,
        message_md: str,
        meta: Dict[str, Any],
    ):
        cur.execute(
            """
            INSERT INTO training.dose_attempt_feedback
              (attempt_id, code, severity, message_md, meta)
            VALUES (%s,%s,%s,%s,%s::jsonb)
            """,
            (attempt_id, code, severity, message_md, json.dumps(meta or {})),
        )
