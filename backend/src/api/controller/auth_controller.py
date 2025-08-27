# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, Tuple
import psycopg2
from database.connection import get_db_connection

def insert_user(email: str, password_hash: str, first_name: str, last_name: str) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (email, password_hash, first_name, last_name),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "23505":
            raise ValueError("Email deja utilise")
        raise ValueError("Erreur base de donnees")
    finally:
        cur.close()
        conn.close()



def find_user_by_email(email: str) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, email, password_hash, is_active FROM users WHERE email = %s;",
            (email,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()



def add_session(user_id: int, token_hash: str, expires_at: Optional[datetime]) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (user_id, token_hash, expires_at))
        sid = cur.fetchone()[0]
        conn.commit()
        return sid
    finally:
        cur.close()
        from database.connection import release_db_connection
        release_db_connection(conn)

def get_session_by_token(token_hash: str) -> Optional[Tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, token_hash, created_at, expires_at
            FROM sessions WHERE token_hash = %s;
        """, (token_hash,))
        return cur.fetchone()
    finally:
        cur.close()
        from database.connection import release_db_connection
        release_db_connection(conn)


def delete_session_by_token(token_hash: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sessions WHERE token_hash = %s;", (token_hash,))
        conn.commit()
    finally:
        cur.close()
        from database.connection import release_db_connection
        release_db_connection(conn)



def delete_all_sessions_for_user(user_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sessions WHERE user_id = %s;", (user_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()