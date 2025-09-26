from database.connection import get_db_connection
from typing import Optional, Tuple, List, Dict, Any

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, first_name, last_name, pseudo, is_active
            FROM public.users
            WHERE id = %s;
        """, (user_id,))
        r = cur.fetchone()
        if not r: return None
        return { "id": r[0], "email": r[1], "first_name": r[2], "last_name": r[3], "pseudo": r[4], "is_active": r[5] }
    finally:
        cur.close()
        conn.close()

def get_all_users():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, first_name, last_name, is_active
            FROM users ORDER BY id ASC;
        """)
        return cur.fetchall()
    finally: 
        cur.close()
        conn.close()

def get_user_by_email(email: str) -> dict | None: 
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
            SELECT id, email, password_hash, first_name, last_name, pseudo,
                    phone_number, address_line1, address_line2, postal_code,
                    city, country, date_of_birth, profile_picture_url,
                    is_active, created_at
            FROM users
            WHERE email = %s
        """,(email,))
        row = cur.fetchone()
        if not row:
            return None
        
        cols = [desc[0] for desc in cur.description ]
        return dict(zip(cols, row))
    finally:
        cur.close()
        conn.close()

def get_roles_by_user_id(user_id: int) -> List[str]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT r.code
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s;
        """, (user_id,))
        rows = cur.fetchall() or []
        return [r[0] for r in rows]
    finally:
        cur.close()
        conn.close()


def get_permissions_by_user_id(user_id: int) -> List[str]:
 
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT DISTINCT p.code
            FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p       ON p.id = rp.permission_id
            WHERE ur.user_id = %s;
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []
        return [r[0] for r in rows]
    finally:
        cur.close()
        conn.close()

def update_user_basic(user_id: int, first_name: str, last_name: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE users SET first_name = %s , last_name = %s WHERE id = %s;
        """, (first_name, last_name, user_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def delete_user(user_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


        