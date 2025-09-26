from typing import Optional, Tuple, List, Dict
from database.connection import get_db_connection

def _row_to_dict(cur, row) -> Dict:
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

def get_by_id(pid: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT id, code, title, summary, category_id, tags, is_published, created_by, created_at, updated_at
                    FROM content.protocols
                    WHERE id = %s ;
        """,(pid,))
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None
    finally:
        cur.close()
        conn.close()

def get_by_code(code: str) -> Optional[Dict]:
    conn= get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT id, code, title, summary, category_id, tags, is_published, created_by, updated_at
                    FROM content.protocols
                    WHERE lower(code) = lower(%s);
        """,(code.strip(),))
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None
    finally:
        cur.close()
        conn.close()

def get_latest_version(protocol_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECR id, version, body_md, changelog, published_at, created_at
                    FROM content.protocol_versions
                    WHERE protocol_id = %s
                    ORDER BY COALESCE(published_at, created_at) DESC , version DESC
                    LIMIT 1;
        """,(protocol_id,))
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None
    finally:
        cur.close()
        conn.close()

def list_protocols(q: Optional[str], category_id: Optional[int],
                   published: Optional[bool], limit: int, offset: int) -> Tuple[int, List[Dict]]:
    conn = get_db_connection(); 
    cur = conn.cursor()

    try:
       where = []
       params = []
       if q: 
        where.append("(title ILIKE %s OR summary ILIKE %s OR search_vector@@ plainto_tsquery('simple', unaccent(%s)))")
        like = f"%{q.strip()}%"; params += [like, like, like, q]
        if category_id is not None:
            where.append("category_id = %s")
            params.append(category_id)
        if published is not None:
            where.append("is_published =%s")
            params.append(published)

        where_sql = ("WHERE " + "AND".join(where)) if where else ""
        cur.execute(f"""
            SELECT id, code, title, summary, category_id, tags, is_published, created_by, created_at, updated_at
                    FROM content.protocols
                    {where_sql}
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s;
        """,(*params, limit, offset))
        rows = cur.fetchall()
        items = [_row_to_dict(cur, r) for r in rows]

        cur.execute(f"SELECT COUNT(*) FROM content.protocols {where_sql}", tuple(params))
        total = cur.fetchone()[0]
        return total, items
    finally:
        cur.close()
        conn.close()

def insert_protocol(data: Dict) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO content.protocols
                    (category_id, code, title, summary, tags, is_published, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)  RETURNING  id, code, title, summary, category_id, tags, is_published, created_by, created_at, updated_at;
        """, (
             data.get("category_id"), data["code"].strip(), data["title"],
            data.get("summary"), data.get("tags", []),
            data.get("is_published", False), data.get("created_by")
        ))
        row = cur.fetchone()
        conn.commit()
        return _row_to_dict(cur, row)
    finally:
        cur.close()
        conn.close()

def insert_version(protocol_id: int, body_md: str, changelog: Optional[str], publish_now: bool) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM content.protocol_versions WHERE protocol_id = %s", (protocol_id))
        next_v = cur.fetchone()
        cur.execute("""
            INSERT INTO content.protocol_versions (protocol_id, version , body_md, changelog, published_at) 
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, version, body_md, changelog, published_at, created_at; 
        """,(protocol_id, next_v, body_md, changelog, "NOW()" if publish_now else None))
        row = cur.fetchone()
        return _row_to_dict(cur, row)
    finally:
        cur.close()
        conn.close()

def update_protocol(pid: int, data: Dict) -> Optional[Dict]:
    sets,vals = [], []
    for k in ("title", "summary","category_id", "tags", "is_published"):
        if k in data and data[k] is not None:
            sets.append(f"{k} = %s")
            vals.append(data[k])
    if not sets:
        return get_by_id(pid)
    vals.append(pid)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"""
            UPDATE content.protocols
                    SET {",".join(sets)}
            WHERE id = %s
            RETURNING id, code, title, summary, category_id, tags, is_published, created_by, created_at, updated_at;
        """, tuple(vals))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None
        conn.commit()
        return _row_to_dict(cur, row)
    finally:
        cur.close()
        conn.close()

def delete_protocol(pid: int) -> bool : 
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM content.protocols WHERE id = %s ;
        """, (pid,))
        ok = cur.rowcount > 0
        conn.commit()
        return ok
    finally:
        cur.close()
        conn.close()

        