from database.connection import get_db_connection
from typing import Optional, Tuple, List

def get_user_by_id(user_id: int) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, first_name , last_name, is_active
            FROM users WHERE id = %s
        """,(user_id, ))
        return cur.fetchone()
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


def get_roles_by_user_id(user_id: int) -> list[str]:
    conn = get_db_connection(); 
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT r.code
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s;
        """, (user_id,))
        return [row[0] for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

def get_premissions_by_user_id(user_id: int) -> list[str]:
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


        