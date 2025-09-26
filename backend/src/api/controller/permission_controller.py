from typing import List, Optional, Tuple
from database.connection import get_db_connection

def list_permissions(limit: int = 100, offset: int = 0, q: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        where = "WHERE code ILIKE %s OR label ILIKE %s" if q else ""
        params = (f"%{q}%", f"%{q}%") if q else ()

        cur.execute(f"SELECT COUNT(*) FROM permissions {where};", params)
        total = cur.fetchone()[0]  # <-- le [0] est crucial

        cur.execute(f"""
            SELECT id, code, label, description, created_at, updated_at
              FROM permissions
              {where}
             ORDER BY code
             LIMIT %s OFFSET %s;
        """, (*params, limit, offset) if params else (limit, offset))
        rows = cur.fetchall()
        return rows, total
    finally:
        cur.close()
        conn.close()

def list_permissions_by_role(role_id:int) -> List[Tuple]:
    if not _role_exists(role_id):
        raise ValueError("Role inconnue")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
                SELECT p.id, p.code, p.label
                FROM public.role_permissions rp
                JOIN public.permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = %s
                ORDER BY p.code ASC
            """, (role_id,))
        return cur.fetchall()
    finally: 
        cur.close()
        conn.close()

def list_role_by_permission(perm_code: str) -> List[Tuple]:
    perm_id= _get_permission_id_by_code(perm_code)
    if not perm_id:
        raise ValueError("Permission inconnue")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT r.id, r.code, r.label
                    FROM role_permissions rp JOIN roles r ON r.id = rp.role_id
                    WHERE rp.permission_id = %s ORDER BY r.code ;
        """, (perm_code, ))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def get_permissions_by_user_id(user_id: int) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT p.code
            FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = %s;
        """, (user_id,))
        if cur.description is None:
            return []
        rows = cur.fetchall()
        return [r[0] for r in rows]
    finally:
        cur.close()
        conn.close

def get_permission_by_code(code: str) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, code, label, description, created_at, updated_at
                    FROM permissions WHERE code = %s;
        """,(code,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

def _get_permission_id_by_code(code: str) -> Optional[int] : 
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM permissions WHERE code = %s;", (code,))
        row = cur.frtchone()
        return row[0] if row else None
    finally:
        cur.close()
        conn.close()

def _role_exists(role_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT 1 FROM roles WHERE id = %s;
        """,(role_id,))
        return cur.fetchone() 
    finally:
        cur.close()
        conn.close()

def create_permission(code: str, label: str, description: Optional[str]) -> int:
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
         INSERT INTO permissions (code, label, description)
                    VALUES (%s, %s, %s)
                RETURNING id;
        """, (code, label, description))
        pid = cur.fetchone()[0]
        conn.commit()
        return pid
    finally: 
        cur.close()
        conn.close()

def add_permission_to_role(role_id: int, perm_code: str) -> bool:
    perm_id = _get_permission_id_by_code(perm_code)
    if not perm_id:
        raise ValueError("Permission inconnue")
    if not _role_exists(role_id):
        raise ValueError("Role inconnue")
    
    conn = get_db_connection()
    cur = conn.cursor()
    try: 

        cur.execute("""
            INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING;
            """,(role_id, perm_code))
        inserted = cur.rowcount > 0
        conn.commit()
        return inserted
    finally:
        cur.close()
        conn.close()

def update_permissions(code: str, label: Optional[str], description: Optional[str]) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            UPDATE permissions SET label = COALESCE (%s, label), 
                    description = COALESCE (%s, description),
                    updated_at = NOW()
                    WHERE code = %s ;
        """, (label, description, code))
        conn.commit()
    finally:
        cur.close()
        conn.close()



def delete_permissions(code: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            DELETE FROM permissions WHERE code = %s;
        """, (code,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def remove_permission_from_role(role_id: int, perm_code: str ) -> bool:
    perm_id = _get_permission_id_by_code(perm_code)
    if not perm_id:
        raise ValueError("Permission inconnue")
    if not _role_exists(role_id):
        raise ValueError("role inconnue")
    
    conn =get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM role_permissions
                    WHERE role_id = %s AND permission_id = %s ;
        """, (role_id, perm_id))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()
