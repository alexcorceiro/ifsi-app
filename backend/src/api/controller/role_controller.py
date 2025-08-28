from typing import List, Optional, Tuple, Dict, Any
from database.connection import get_db_connection, release_db_connection

def list_roles() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, label, description
            FROM roles
            ORDER BY code;
        """)
        rows = cur.fetchall()
        return [
            {"id": r[0], "code": r[1], "label": r[2], "description": r[3]}
            for r in rows
        ]
    finally:
        cur.close()
        conn.close()

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




def create_role(code: str, label: str, description: Optional[str]) -> Dict[str, Any]:
    code = code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM roles WHERE code=%s;", (code,))
        if cur.fetchone():
            raise ValueError("CODE_ALREADY_EXISTS")

        cur.execute("""
            INSERT INTO roles (code, label, description)
            VALUES (%s, %s, %s)
            RETURNING id, code, label, description;
        """, (code, label, description))
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "code": row[1], "label": row[2], "description": row[3]}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def update_role(code: str, label: Optional[str], description: Optional[str]) -> Dict[str, Any]:
    code = code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM roles WHERE code=%s;", (code,))
        row = cur.fetchone()
        if not row:
            raise ValueError("ROLE_NOT_FOUND")

        cur.execute("""
            UPDATE roles
               SET label = COALESCE(%s, label),
                   description = COALESCE(%s, description)
             WHERE code = %s
         RETURNING id, code, label, description;
        """, (label, description, code))
        out = cur.fetchone()
        conn.commit()
        return {"id": out[0], "code": out[1], "label": out[2], "description": out[3]}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def delete_role(code: str) -> None:
    code = code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM roles WHERE code=%s RETURNING id;", (code,))
        row = cur.fetchone()
        if not row:
            raise ValueError("ROLE_NOT_FOUND")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def get_permissions_by_role_code(role_code: str) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.code
            FROM roles r
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p       ON p.id = rp.permission_id
            WHERE r.code = %s
            ORDER BY p.code;
        """, (role_code.strip().lower(),))
        return [row[0] for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

def assing_permission(role_code: str, permission_code: str) -> None:
    role_code = role_code.strip().lower()
    permission_code = permission_code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM roles WHERE code=%s", (role_code,))
        r = cur.fetchone()
        if not r:
            raise ValueError("ROLE_NOT_FOUND")
        role_id = r[0]

        cur.execute("SELECT id FROM permissions WHERE code =%s", (permission_code,))
        p = cur.fetchone()
        if not p:
            raise ValueError("PERMISSION_NOT_FOUND")
        perm_id = p[0]

        cur.execute("""
            INSERT INTO role_permission (role_id, permission_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING ;
        """, (role_id, perm_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def revoke_permission(role_code: str, permission_code: str) -> None:
    role_code = role_code.strip().lower()
    permission_code = permission_code.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()

    try: 
        cur.execute("SELECT id FROM roles WHERE code = %s", (role_code,))
        r = cur.fetchone()
        if not r :
            raise ValueError("ROLE_NOT_FOUND")
        role_id = r[0]

        cur.execute("SELECT id  FROM permissions WHERE code = %s", (permission_code, ))
        p = cur.fetchone()
        if not p: 
            raise ValueError("PERMISSION_NOT_FOUND")
        perm_id = p[0]

        cur.execute("""
            DELETE FROM role_permission  WHERE role_id=%s AND permission_id=%s;
        """,(role_id, perm_id))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        conn.close()