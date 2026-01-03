from typing import Optional, Tuple, List
from database.connection import get_db_connection

def create_program(code: str, label: str, ects_total: Optional[int]):
    code = code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT 1 FROM academics.programs WHERE code=%s", (code, ))
        if cur.fetchone(): raise ValueError("CODE_ALREADY_EXISTS")
        cur.execute("""
            INSERT INTO academics.programs(code, label,ects_total)
                    VALUES (%s,%s, %s)
                    RETURNING id, code, label, ects_total, created_at
            """,(code, label, ects_total))
        row = cur.fetchone()
        conn.commit()
        return row
    finally: 
        cur.close()
        conn.close()

def update_program(pid: int, label: Optional[str], ects_total: Optional[int]):
    conn= get_db_connection()
    cur= conn.cursor()

    try: 
        cur.execute("SELECT id FROM academics.programs WHERE id=%s", (pid,))
        if not cur.fetchone():
            raise ValueError("PROGRAM_NOT_FOUND")
        cur.execute("""
          UPDATE academics.programs
             SET label = COALESCE(%s, label),
                 ects_total = COALESCE(%s, ects_total)
           WHERE id = %s
           RETURNING id, code, label, ects_total, created_at
        """, (label, ects_total, pid))
        row = cur.fetchone()
        conn.commit()
        return row
    finally:
        cur.close()
        conn.close()

def get_program(pid: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, label, ects_total, created_at
                    FROM academics.programs WHERE id=%s;
        """,(pid, ))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

def get_list_programs(limit: int, offset: int, q: Optional[str]) -> Tuple[List[tuple], int]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        where, params = "", []
        if q:
            where = "WHERE code ILIKE %s OR label ILIKE %s"
            params = [f"%{q}%", f"%{q}%"]
        cur.execute(f"SELECT COUNT(*) FROM academics.programs {where}", params)
        total = cur.fetchone()[0]
        cur.execute(f"""
          SELECT id, code, label, ects_total, created_at
          FROM academics.programs
          {where}
          ORDER BY created_at DESC
          LIMIT %s OFFSET %s
        """, (*params, limit, offset) if params else (limit, offset))
        return cur.fetchall(), total
    finally:
        cur.close()
        conn.close()

def delete_program(pid: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM academics.programs WHERE id=%s RETURNING id; ", (pid,))
        if not cur.fetchone(): 
            raise ValueError("PROGRAM_NOT_FOUND")
        conn.commit()

    finally:
        cur.close()
        conn.close()
        