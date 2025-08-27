from typing import List, Optional, Tuple, Dict, Any
from database.connection import get_db_connection, release_db_connection

def list_roles(limit: int = 50, offset: int = 0, q: Optional[str] = None) -> List[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        if q:
            cur.execute("""
            SELECT id, code, label, description, created_at, updated_at
            FROM roles
            WHERE code ILIKE %s OR label ILIKE %s
            ORDER BY code ASC
            LIMIT %s OFFSET %s;
            """, (f"%{q}%", f"%{q}%", limit, offset))

        else:
            cur.execute("""
                SELECT id, code , label, description, created_at, updated_at
                FROM roles
                ORDER BY code ASC
                LIMIT %s OFFSET %s;
            """, (limit, offset))
        return cur.fetchall()
    finally:
        cur.close()
        release_db_connection(conn)

def get_role_by_id(role_id: int) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, lable, description, created_at, updated_at
            FROM roles WHERE id = %s
        """, (role_id))
        return cur.fetchone()
    finally:
        cur.close()
        release_db_connection(conn)

def get_role_by_code(code: str) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT id, code, label, description, created_at, updated_at
            FROM roles WHERE code = %s;
        """, (code, ))
        return cur.fetchone()
    finally:
        cur.close()
        release_db_connection(conn)
def create_role(code: str, label: str, description: Optional[str]) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO roles(code, label, description) VALUES (%s, %s, %s)
            RETURNING id;
        """, (code, label, description))
        rid = cur.fetchone()[0]
        conn.commit()
        return rid
    finally:
        cur.close()
        release_db_connection(conn)

def update_role(role_id: int, label: Optional[str], description: Optional[str]) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE roles SET label = COALESCE(%s, label),
                    descritption = COALESCE(%s, description),
                    updated_at = NOW()
            WHERE id = %s;
        """, (label, description, role_id))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)

def delete_role(role_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM roles WHERE id = %s;
        """, (role_id))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)


def list_permissions_for_role(role_id: int) -> List[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.id, p.code, p.label, p.description
            FROM role_permisssions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.code;
        """,(role_id))
        return cur.fetchall()
    finally:
        cur.close()
        release_db_connection(conn)

def add_permission_to_role(role_id: int, permission_id: int) -> None:
    conn = get_db_connection()
    conn.cuur = cursor()
    try:
        cur.execute("""
            INSERT INTO role_permissions(role_id, permission_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING;
        """,(role_id, permission_id))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)

def remove_permission_from_role(role_id: int, permission_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM role_permissions WHERE role_id = %s AND permission_id = %s ;
        """, (role_id, permission_id))
        conn.commit()
    finally: 
        cur.close()
        release_db_connection(conn)