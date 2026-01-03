from __future__ import annotations
from typing import Optional, List, Dict, Any

def _to_dict_many(cur, rows):
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in rows]


def _row_id(row) -> int:
    if row is None:
        raise ValueError("Aucune ligne retournée par RETURNING id")
    return row["id"] if isinstance(row, dict) else row[0]


def _to_dict(cur, row):
    """Convertit une row tuple en dict via cur.description (compatible dict-cursor aussi)."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cols = [d[0] for d in cur.description] if cur.description else []
    return dict(zip(cols, row))


def _fetchone_dict(cur) -> Optional[Dict[str, Any]]:
    return _to_dict(cur, cur.fetchone())


def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in rows]


class CaseRepo:
    # ---------------- CASE ----------------
    @staticmethod
    def get_case(cur, case_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM training.clinical_cases WHERE id=%s", (case_id,))
        return _fetchone_dict(cur)

    # ---------------- ATTEMPTS ----------------
    @staticmethod
    def create_attempt(cur, *, user_id: int, case_id: int) -> int:
        cur.execute(
            """
            INSERT INTO training.case_attempts (user_id, case_id, score, completed)
            VALUES (%s, %s, 0, FALSE)
            RETURNING id
            """,
            (user_id, case_id),
        )
        return _row_id(cur.fetchone())

    @staticmethod
    def get_attempt(cur, attempt_id: int):
        cur.execute("SELECT * FROM training.case_attempts WHERE id=%s", (attempt_id,))
        return _to_dict(cur, cur.fetchone())

    @staticmethod
    def update_attempt_status(cur, *, attempt_id: int, score: float, completed: bool) -> None:
        cur.execute(
            """
            UPDATE training.case_attempts
            SET score=%s, completed=%s
            WHERE id=%s
            """,
            (score, completed, attempt_id),
        )

    # alias si tu l'utilises ailleurs
    @staticmethod
    def update_attempt(cur, *, attempt_id: int, score: float, completed: bool) -> None:
        CaseRepo.update_attempt_status(cur, attempt_id=attempt_id, score=score, completed=completed)

    # ---------------- STEPS ----------------
    @staticmethod
    def list_steps(cur, case_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT * FROM training.case_steps
            WHERE case_id=%s
            ORDER BY position ASC
            """,
            (case_id,),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def get_step(cur, step_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM training.case_steps WHERE id=%s", (step_id,))
        return _fetchone_dict(cur)

    @staticmethod
    def get_step_by_position(cur, case_id: int, position: int) -> Optional[Dict[str, Any]]:
        cur.execute(
            """
            SELECT * FROM training.case_steps
            WHERE case_id=%s AND position=%s
            """,
            (case_id, position),
        )
        return _fetchone_dict(cur)

    @staticmethod
    def count_steps(cur, case_id: int) -> int:
        cur.execute("SELECT COUNT(*) AS n FROM training.case_steps WHERE case_id=%s", (case_id,))
        row = cur.fetchone()
        return int(row["n"] if isinstance(row, dict) else row[0])

    # ---------------- CHOICES ----------------
    @staticmethod
    def list_choices(cur, step_id: int):
        cur.execute("""
            SELECT * FROM training.case_step_choices
            WHERE step_id=%s
            ORDER BY position ASC
        """, (step_id,))
        return _to_dict_many(cur, cur.fetchall())

    @staticmethod
    def get_choice(cur, choice_id: int) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT * FROM training.case_step_choices WHERE id=%s", (choice_id,))
        return _fetchone_dict(cur)

    # ---------------- ANSWERS ----------------
    @staticmethod
    def list_answers(cur, attempt_id: int) -> List[Dict[str, Any]]:
        cur.execute(
            """
            SELECT * FROM training.case_step_answers
            WHERE attempt_id=%s
            ORDER BY created_at ASC
            """,
            (attempt_id,),
        )
        return _fetchall_dict(cur)

    @staticmethod
    def get_answer(cur, *, attempt_id: int, step_id: int) -> Optional[Dict[str, Any]]:
        cur.execute(
            """
            SELECT * FROM training.case_step_answers
            WHERE attempt_id=%s AND step_id=%s
            """,
            (attempt_id, step_id),
        )
        return _fetchone_dict(cur)

    @staticmethod
    def insert_or_update_answer(
        cur,
        *,
        attempt_id: int,
        step_id: int,
        selected_choice_id: Optional[int],
        free_answer_text: Optional[str],
        is_correct: bool,
    ) -> int:
        cur.execute(
            """
            INSERT INTO training.case_step_answers
              (attempt_id, step_id, selected_choice_id, free_answer_text, is_correct)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (attempt_id, step_id)
            DO UPDATE SET
              selected_choice_id = EXCLUDED.selected_choice_id,
              free_answer_text   = EXCLUDED.free_answer_text,
              is_correct         = EXCLUDED.is_correct,
              created_at         = NOW()
            RETURNING id
            """,
            (attempt_id, step_id, selected_choice_id, free_answer_text, is_correct),
        )
        return _row_id(cur.fetchone())

    # alias (si ton service appelle upsert_answer)
    @staticmethod
    def upsert_answer(
        cur,
        *,
        attempt_id: int,
        step_id: int,
        selected_choice_id: Optional[int],
        free_answer_text: Optional[str],
        is_correct: bool,
    ) -> int:
        return CaseRepo.insert_or_update_answer(
            cur,
            attempt_id=attempt_id,
            step_id=step_id,
            selected_choice_id=selected_choice_id,
            free_answer_text=free_answer_text,
            is_correct=is_correct,
        )

    @staticmethod
    def count_correct_answers(cur, attempt_id: int) -> int:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM training.case_step_answers
            WHERE attempt_id=%s AND is_correct=TRUE
            """,
            (attempt_id,),
        )
        row = cur.fetchone()
        return int(row["n"] if isinstance(row, dict) else row[0])

    @staticmethod
    def count_answers(cur, attempt_id: int) -> int:
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM training.case_step_answers
            WHERE attempt_id=%s
            """,
            (attempt_id,),
        )
        row = cur.fetchone()
        return int(row["n"] if isinstance(row, dict) else row[0])

    # compat si tu utilises encore l'ancien nom
    @staticmethod
    def count_answer(cur, attempt_id: int) -> int:
        return CaseRepo.count_answers(cur, attempt_id)
