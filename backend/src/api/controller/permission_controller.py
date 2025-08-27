from typing import List, Optional, Tuple
from database.connection import get_db_connection, release_db_connection

def list_permissions(limit: int = 100, offset: int = 0, q: Optional[str] = None ) -> List[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if q:
            cur.execute("""
                SELECT id, code, label, description, created_at, updated_at
                FROM permissions WHERE code ILIKE %s OR label ILIKE %s
                ORDER BY code
                LIMIT %s OFFSET %s;
            """, (f"%{q}%", f"%{q}%", limit, offset))
        else : 
            cur.execute("""
                SELECT id, code, label, description, created_at, updated_at
                FROM permissions ORDER BY code LIMIT %s OFFSET %s;
            """, (limit, offset))
            return cur.fetchall()
    finally:
        cur.close()
        release_db_connection(conn)

def get_permission_by_code(code: str) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, label, descritpion, created_at, updated_at
                    FROM permissions WHERE code = %s ;
        """, (code, ))
        return cur.fetchone()
    finally:
        cur.close()
        release_db_connection(conn)

def create_permission(code: str, label: str, description: Optional[str]) -> int :
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO permissions (code, label, description) VALUES (%s, %s, %s) RETURNING id;
        """, (code, label, description))
        pid = cur.getchone()[0]
        conn.commit()
        return pid
    finally:
        cur.close()
        release_db_connection(conn)

def update_permission(code: str, label: Optional[str], description: Optional[str]) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE permissions SET label = COALESCE(%s, label),
                    description = COALESCE(%s, description),
                    updated_at = NOW()
                    WHERE code = %s;
        """,(label, description, code))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)

def delete_permission(code: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM permissions WHERE code = %s
        """, (code))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)