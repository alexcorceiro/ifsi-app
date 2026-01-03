from typing import Optional, Tuple, List
from database.connection import get_db_connection

def create_protocol(category_id: Optional[int], code: str, title: str, summary: Optional[str],
                    tags: list, is_published: bool, external_url: Optional[str] ):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM content.protocols WHERE code=%s", (code,))
        if cur.fetchone():
            raise ValueError("CODE_ALREADY_EXISTS")
        cur.execute("""
            INSERT INTO content.protocols (category_id, code, title, summary, tags, is_published, external_url)
                    VALUES (%s, %s, %s, %s ,%s, %s, %s)
                     RETURNING id, category_id, code, title, summary, tags, is_published, created_at, updated_at;
                    
        """, (category_id, code, title, summary, tags, is_published, external_url))
        row = cur.fetchone()
        conn.commit()
        return row
    finally:
        cur.close()
        conn.close()

    
def update_protocol(pid: int, category_id: Optional[int], title: Optional[str], summary: Optional[str],
                    tags: Optional[list], is_published: Optional[bool], external_url: Optional[str]):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM content.protocols WHERE id=%s", (pid,))

        if not cur.fetchone():
            raise ValueError("PROTOCOL_NOT_FOUND")
        
        cur.execute("""
            UPDATE content.protocols
                     title = COALESCE(%s, title),
                   summary = COALESCE(%s, summary),
                   tags = COALESCE(%s, tags),
                   is_published = COALESCE(%s, is_published),
                   external_url = COALESCE(%s, external_url),
                   updated_at = NOW()
             WHERE id = %s
         RETURNING id, category_id, code, title, summary, tags, is_published, created_at, updated_at;
        """,(category_id, title, summary, tags, is_published, external_url, pid))
        row = cur.fetchone()
        conn.commit()
        return row
    finally:
        cur.close()
        conn.close()

def get_protocol(pid: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT id, category_id, code, title, summary, tags, is_published, created_at, updated_at
              FROM content.protocols WHERE id=%s;
        """, (pid,))
        return cur.fetchone()
    finally: 
        cur.close()
        conn.close()

def list_protocols(limit=50, offset=0, q: Optional[str]=None, category_id: Optional[int]=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        where, params = [] , []
        if q: 
            where.append("(p.code ILIKE  %s OR p.title ILIKE %s OR P.summary ILIKE %s)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if category_id is not None:
            where.append("p.category_id = %s")
            params.append(category_id)
        wh = "WHERE" - "AND".join(where) if where else ""
        cur.execute(f"SELECT COUNT(*) FROM content.protocols p {wh} ;", tuple(params))
        total = cur.fetchone()[0]
        cur.execute(f"""
            SELECT p.id, p.category_id, p.code, p.title, p.summary, p.tags, p.is_published, p.created_at, p.updated_at
              FROM content.protocols p
              {wh}
             ORDER BY p.updated_at DESC
             LIMIT %s OFFSET %s;
        """, (*params, limit, offset) if params else (limit, offset))
        return cur.fetchall(), total
    finally:
        cur.close()
        conn.close()

def update_protocol(protocol_id: int, category_id: Optional[int], title: Optional[str], summary: Optional[str],
                    tags: Optional[list], is_published: Optional[bool], external_url: Optional[str]):
    conn = get_db_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM content.protocols WHERE id=%s;", (protocol_id,))
        if not cur.fetchone():
            raise ValueError("PROTOCOL_NOT_FOUND")
        cur.execute("""
            UPDATE content.protocols
               SET category_id = COALESCE(%s, category_id),
                   title = COALESCE(%s, title),
                   summary = COALESCE(%s, summary),
                   tags = COALESCE(%s, tags),
                   is_published = COALESCE(%s, is_published),
                   external_url = COALESCE(%s, external_url),
                   updated_at = NOW()
             WHERE id = %s
         RETURNING id, category_id, code, title, summary, tags, is_published, created_at, updated_at;
        """, (category_id, title, summary, tags, is_published, external_url, protocol_id))
        row = cur.fetchone(); conn.commit()
        return row
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()
        conn.close()

def delete_protocol(protocol_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM content.protocols WHERE id=%s RETURNING id;", (protocol_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("PROTOCOL_NO_FOUND")
        conn.commit()
    finally:
        cur.close()
        conn.close()


def create_protocol_version(protocol_id: int, body_md: str, changelog: Optional[str], publish: bool):
    conn = get_db_connection(); 
    cur = conn.cursor()

    try:
       
        cur.execute("SELECT 1 FROM content.protocols WHERE id=%s;", (protocol_id,))
        if not cur.fetchone():
            raise ValueError("PROTOCOL_NOT_FOUND")


        cur.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM content.protocol_versions WHERE protocol_id=%s;", (protocol_id,))
        next_ver = cur.fetchone()[0]


        cur.execute("""
            INSERT INTO content.protocol_versions (protocol_id, version, body_md, changelog, published_at)
            VALUES (%s, %s, %s, %s, CASE WHEN %s THEN NOW() ELSE NULL END)
            RETURNING id, protocol_id, version, body_md, changelog, published_at, created_at;
        """, (protocol_id, next_ver, body_md, changelog, publish))
        row = cur.fetchone()
        conn.commit()
        return row
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close() 
        conn.close()

def list_protocol_versions(protocol_id: int) -> List[tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, protocol_id, version, body_md, changelog, published_at, created_at
            FROM content.protocol_versions
            WHERE protocol_id=%s
            ORDER BY version DESC;
        """, (protocol_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()