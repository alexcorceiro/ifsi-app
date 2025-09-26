from typing import Optional, Tuple, List, Dict
from database.connection import get_db_connection


def insert_category(data: Dict) -> Dict:
    conn = get_db_connection()
    cur= conn.cursor()
    try:
       cur.execute("""
            INSERT INTO content.categories (code, label, description)
                   VALUES (trim(%s), %s, %s)
            RETURNING id, code, label, description, created_at, updated_at;
        """.replace("$1", "%s"), (data["code"].strip(), data["label"], data.get("description")))
       row = cur.fetchone()
       conn.commit()
       cols = [d[0] for d in cur.description]
       return dict(zip(cols, row))
    
    finally:
        cur.close()
        conn.close()

def get_category_by_id(cid: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, code, label, description, created_at, updated_at
            FROM content.categories
            WHERE id = %s;
            """,
            (cid,)
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close()
        conn.close()

def get_category_by_code(code: str) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, label, description, created_at, updated_at
                    FROM content.categories
            WHERE lower(code) = lower (%s);
        """,(code.strip(),))
        row = cur.fetchone()
        if not row:
            return None
        clos = [d[0] for d in cur.description]
        return dict(zip(clos, row))
    finally:
        cur.close()
        conn.close()

def list_category(search: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if search:
            like = f"%{search.strip()}%"
            cur.execute(
                """
                SELECT id, code, label, description, created_at, updated_at
                FROM content.categories
                WHERE code ILIKE %s OR label ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """,
                (like, like, limit, offset)
            )
            items = cur.fetchall()
            cur.execute(
                """
                SELECT COUNT(*) FROM content.categories
                WHERE code ILIKE %s OR label ILIKE %s;
                """,
                (like, like)
            )
        else:
            cur.execute(
                """
                SELECT id, code, label, description, created_at, updated_at
                FROM content.categories
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset)
            )
            items = cur.fetchall()
            cur.execute("SELECT COUNT(*) FROM content.categories;")
        total = cur.fetchone()[0]
        cols = [d[0] for d in cur.description] if items else \
               ["id","code","label","description","created_at","updated_at"]
        return total, [dict(zip(cols, r)) for r in items]
    finally:
        cur.close()
        conn.close()

def update_category(cid: int, data: Dict) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE content.categories
                    SET label = COALESCE(%s, label)
                    description = COALESCE(%s, description)
            WHERE id = %s
                    RETURNING id, code, label, description, created_at, updated_at;
        """,(data.get("label"), data.get("description"), cid))
        row = cur.fetchone()
        if not row: 
            conn.rollback()
            return None
        conn.commit()
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close()
        conn.close()

def delete_category(cid: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM content.categories WHERE id = %s;", (cid,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()