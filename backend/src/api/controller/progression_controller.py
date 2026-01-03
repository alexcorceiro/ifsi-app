from database.connection import get_db_connection

def upsert_progress(user_id: int, lesson_id: int, status: str):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO academics.lesson_progress(user_id, lesson_id, status, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (user_id, lesson_id)
                    DO UPDATE SET status = EXECLUDED.status , updated_at = NOW()
                    RETURNING user_id, lesson_id, status, updated_at ;
        """,(user_id, lesson_id, status))
        row = cur.fetchone()
        conn.commit()
        return row
    finally:
        cur.close()
        conn.close()

def get_progress(user_id: int, lesson_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT user_id, lesson_id, status, updated_at
                    FROM academics.lesson_progress
                    WHERE user_id=%s AND lesson_id=%s;
        """, (user_id, lesson_id))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

        