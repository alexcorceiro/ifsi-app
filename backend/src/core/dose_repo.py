from typing import Optional, Dict, Any
import json

class DoseRepo:
    @staticmethod
    def insert_calculation(cur, *, user_id: Optional[int], context: str,
                           exercise_id: Optional[int], case_id: Optional[int],
                           patient_age_y, weight_kg, drug_name: str,
                           dose_input: Dict[str, Any], dose_result: Dict[str, Any]) -> int:

        cur.execute(
            """
            INSERT INTO core.dose_calculations
              (user_id, context, exercise_id, case_id, patient_age_y, weight_kg,
               drug_name, dose_input, dose_result)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
            RETURNING id
            """,
            (
                user_id, context, exercise_id, case_id,
                patient_age_y, weight_kg,
                drug_name.strip(),
                json.dumps(dose_input),
                json.dumps(dose_result),
            )
        )
        row = cur.fetchone()
        return row["id"] if isinstance(row, dict) else row[0]

    @staticmethod
    def get_calculation(cur, calc_id: int):
        cur.execute("SELECT * FROM core.dose_calculations WHERE id=%s", (calc_id,))
        return cur.fetchone()

    @staticmethod
    def list_calculations(cur, *, user_id: Optional[int], limit: int, offset: int):
        if user_id is not None:
            cur.execute(
                """
                SELECT * FROM core.dose_calculations
                WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )
        else:
            cur.execute(
                """
                SELECT * FROM core.dose_calculations
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
        return cur.fetchall()

    # ✅ Nouveau : update (notes + context)
    @staticmethod
    def update_calculation(cur, calc_id: int, *, notes: Optional[str], context: Optional[str]):
        # On construit dynamiquement pour ne mettre à jour que ce qui est fourni
        fields = []
        params = []

        if notes is not None:
            fields.append("notes=%s")
            params.append(notes)

        if context is not None:
            fields.append("context=%s")
            params.append(context)

        if not fields:
            return None  # rien à update

        params.append(calc_id)

        q = f"""
            UPDATE core.dose_calculations
            SET {", ".join(fields)}
            WHERE id=%s
            RETURNING *
        """
        cur.execute(q, tuple(params))
        return cur.fetchone()

    # ✅ Nouveau : delete
    @staticmethod
    def delete_calculation(cur, calc_id: int) -> bool:
        cur.execute("DELETE FROM core.dose_calculations WHERE id=%s RETURNING id", (calc_id,))
        row = cur.fetchone()
        return bool(row)
