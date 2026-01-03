from typing import Optional, Tuple, List
from database.connection import get_db_connection, release_db_connection

def create_ue(program_id: int, code: str, title: str, year_no: int, sem_no: int, ects, description):
    code = code.strip().lower()
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM academics.programs WHERE id=%s", (program_id,))
        if not cur.fetchone(): raise ValueError("PROGRAM_NOT_FOUND")
        cur.execute("SELECT 1 FROM academics.ue WHERE program_id=%s AND code=%s", (program_id, code))
        if cur.fetchone(): raise ValueError("CODE_ALREADY_EXISTS")
        cur.execute("""
          INSERT INTO academics.ue(program_id, code, title, year_no, sem_no, ects, description)
          VALUES (%s,%s,%s,%s,%s,%s,%s)
          RETURNING id, program_id, code, title, year_no, sem_no, ects, description, created_at
        """, (program_id, code, title, year_no, sem_no, ects, description))
        row = cur.fetchone(); conn.commit(); return row
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); release_db_connection(conn)

def update_ue(ue_id: int, title: Optional[str], year_no: Optional[int], sem_no: Optional[int], ects, description):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM academics.ue WHERE id=%s", (ue_id,))
        if not cur.fetchone(): raise ValueError("UE_NOT_FOUND")
        cur.execute("""
          UPDATE academics.ue
             SET title = COALESCE(%s, title),
                 year_no = COALESCE(%s, year_no),
                 sem_no  = COALESCE(%s, sem_no),
                 ects    = COALESCE(%s, ects),
                 description = COALESCE(%s, description)
           WHERE id = %s
       RETURNING id, program_id, code, title, year_no, sem_no, ects, description, created_at
        """, (title, year_no, sem_no, ects, description, ue_id))
        row = cur.fetchone(); conn.commit(); return row
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); release_db_connection(conn)

def get_ue(ue_id: int):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("""
          SELECT id, program_id, code, title, year_no, sem_no, ects, description, created_at
          FROM academics.ue WHERE id=%s
        """, (ue_id,)); return cur.fetchone()
    finally:
        cur.close(); release_db_connection(conn)

def list_ue(limit: int, offset: int, q: Optional[str], program_id: Optional[int], year_no: Optional[int], sem_no: Optional[int]) -> Tuple[List[tuple], int]:
    conn = get_db_connection(); cur = conn.cursor()
    try:
        filters, params = [], []
        if program_id: filters.append("u.program_id=%s"); params.append(program_id)
        if year_no:    filters.append("u.year_no=%s");    params.append(year_no)
        if sem_no:     filters.append("u.sem_no=%s");     params.append(sem_no)
        if q:
            filters.append("(u.code ILIKE %s OR u.title ILIKE %s)")
            params += [f"%{q}%", f"%{q}%"]
        where = "WHERE " + " AND ".join(filters) if filters else ""
        cur.execute(f"SELECT COUNT(*) FROM academics.ue u {where}", params)
        total = cur.fetchone()[0]
        cur.execute(f"""
          SELECT u.id, u.program_id, u.code, u.title, u.year_no, u.sem_no, u.ects, u.description, u.created_at
          FROM academics.ue u
          {where}
          ORDER BY u.year_no, u.sem_no, u.code
          LIMIT %s OFFSET %s
        """, (*params, limit, offset) if params else (limit, offset))
        return cur.fetchall(), total
    finally:
        cur.close(); release_db_connection(conn)

def delete_ue(ue_id: int):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM academics.ue WHERE id=%s RETURNING id", (ue_id,))
        if not cur.fetchone(): raise ValueError("UE_NOT_FOUND")
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); release_db_connection(conn)
