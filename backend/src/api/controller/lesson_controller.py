from typing import Optional, Tuple, List
from database.connection import get_db_connection


def create_lesson(course_id: Optional[int], code: str, title: str, summary: Optional[str], body_md: Optional[str]):
    code = code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()

    try: 
        cur.execute("SELECT 1 FROM academics.lesssons WHERE code=%s",(code,))
        if cur.fetchone():
            raise ValueError("CODE_ALREADY_EXISTS")
        cur.execute("""
            INSERT INTO academics.lessons (course_id, code, title, summary, body_md)
                    VALUES (%s, %s, %s , %s, %s)
                    RETURNING id, course_id, code, title, summary, body_md, created_at, updated_at;
        """, (course_id, code, title, summary, body_md))
        row = cur.fetchone()
        conn.commit()
        return row 
    finally:
        cur.close()
        conn.close()

def update_lesson(lesson_id: int, course_id: Optional[int], title: Optional[str], summary: Optional[str], body_md: Optional[str]):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM academics.lessons WHERE id=%s", (lesson_id, ))
        if not cur.fetchone():
            raise ValueError("LESSON_NOT_FOUND")
        cur.execute("""
            UPDATE academics.lessons
               SET course_id = COALESCE(%s, course_id),
                   title     = COALESCE(%s, title),
                   summary   = COALESCE(%s, summary),
                   body_md   = COALESCE(%s, body_md),
                   updated_at= NOW()
             WHERE id = %s
         RETURNING id, course_id, code, title, summary, body_md, created_at, updated_at;
        """, (course_id, title, summary, body_md, lesson_id))
        row = cur.fetchone(); conn.commit()
        return row
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()
        conn.close()

def get_lesson(lesson_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try: 
        cur.execute("""
            SELECT id, course_id, code, title, summary, body_md, created_at, updated_at
                    FROM academics.lessons
                    WHERE id= %s;
        """,(lesson_id, ))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

def get_list_lessons(limit: int = 50, offset: int = 0, q: Optional[str] = None, course_id: Optional[int] = None) -> Tuple[List[tuple], int]:
    conn = get_db_connection(); 
    cur = conn.cursor()

    try: 
        wh, params = [], []
        if q : 
            wh.append("(l.code ILIKE %s OR l.title ILIKE %s OR l.summary ILIKE %s)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if course_id is not None:
            wh.append("l.course_id = %s")
            params.append(course_id)
        where = "WHERE " + " AND ".join(wh) if wh else ""

        cur.execute(f"SELECT COUNT (*) FROM academics.lessons l {where};", tuple(params))
        total = cur.fetchone()[0]

        cur.execute(f"""
            SELECT l.id, l.course_id, l.code, l.title, l.summary, l.body_md, l.created_at, l.updated_at
            FROM academics.lessons l
            {where}
            ORDER BY l.updated_at DESC
            LIMIT %s OFFSET %s;
        """, (*params, limit, offset) if params else (limit, offset))
        rows = cur.fetchall()
        return rows, total
    finally:
        cur.close()
        conn.close()

def delete_lesson(lesson_id: int):
    conn = get_db_connection()
    cur = conn.cursor()

    try: 
        cur.execute("DELETE FROM academics.lessons WHERE id=%s RETURNING id;", (lesson_id,))
        row = cur.fetchone()
        if not row: 
            raise ValueError("LESSON_NOT_FOUND")
        conn.commit()
    finally: 
        cur.close()
        conn.close()