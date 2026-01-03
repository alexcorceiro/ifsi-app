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

def list_categories(limit: int = 100, offset: int = 0, q: Optional[str] = None) -> Tuple[List[tuple], int]:
    conn = get_db_connection(); cur = conn.cursor()
    try:
        where, params = "", ()
        if q:
            where = "WHERE c.code ILIKE %s OR c.label ILIKE %s"
            params = (f"%{q}%", f"%{q}%")
        cur.execute(f"SELECT COUNT(*) FROM content.categories c {where};", params)
        total = cur.fetchone()[0]
        cur.execute(f"""
            SELECT c.id, c.code, c.label, c.description, c.created_at, c.updated_at
              FROM content.categories c
              {where}
             ORDER BY c.code
             LIMIT %s OFFSET %s;
        """, (*params, limit, offset) if params else (limit, offset))
        rows = cur.fetchall()
        return rows, total
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