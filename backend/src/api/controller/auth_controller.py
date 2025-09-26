# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional, Tuple , Dict, Any
from fastapi import HTTPException
from database.connection import get_db_connection
from utils.jwt import verify_access_token, hash_token

def insert_user(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO public.users (
                email, password_hash, first_name, last_name, pseudo,
                phone_number, address_line1, address_line2, postal_code,
                city, country, date_of_birth
            )
            VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(pseudo)s,
                    %(phone_number)s, %(address_line1)s, %(address_line2)s, %(postal_code)s,
                    %(city)s, %(country)s, %(date_of_birth)s)
            RETURNING id, email, first_name, last_name, pseudo, is_active;
        """, data)
        row = cur.fetchone()
        conn.commit()
        return {
            "id": row[0], "email": row[1], "first_name": row[2],
            "last_name": row[3], "pseudo": row[4], "is_active": row[5]
        }
    finally:
        cur.close()
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, password_hash, first_name, last_name, pseudo, is_active
            FROM public.users
            WHERE email = %s
            LIMIT 1;
        """, (email,))
        r = cur.fetchone()
        if not r: return None
        return {
            "id": r[0], "email": r[1], "password_hash": r[2],
            "first_name": r[3], "last_name": r[4], "pseudo": r[5], "is_active": r[6]
        }
    finally:
        cur.close()
        conn.close()



def add_session(user_id: int, token_hash: str, expires_at: datetime) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO public.sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (user_id, token_hash, expires_at))
        sid = cur.fetchone()[0]
        conn.commit()
        print(f"[SESSION] insert OK user_id={user_id} sid={sid}")
        return sid
    except Exception as e:
        conn.rollback()
        print("[SESSION-INSERT-ERROR]", repr(e))
        raise
    finally:
        cur.close()
        conn.close()

def get_session_by_token_hash(token_hash: str) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
              SELECT id, user_id, token_hashn, expires_at, created_at
                    FROM sessions
              WHERE token_hash = %s
                    AND (expires_at IS NULL OR expires_at > NOW() )
              LIMIT 1;
        """, (token_hash,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close()
        conn.close()

def get_active_session_by_user_id(user_id: int) -> dict | None:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, user_id, token_hash, created_at, expires_at
                    FROM sessions WHERE user_id= %s
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY created_at DESC LIMIT 1;
        """,(user_id))
        row = cur.fetchone()
        if not row:
            return None
        clos = [d[0] for d in cur.description]
        return dict(zip(clos, row))
    finally:
        cur.close()
        conn.close()

def has_any_active_session(user_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 1 
            FROM sessions 
            WHERE user_id = %s AND (expires_at IS NULL OR expires_at > NOW())
            LIMIT 1
        """,(user_id))
        return cur.fetchone() 
    finally:
        cur.close()
        conn.close()


def fetch_me_if_session_active(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    try: 
        cur.execute("""
           SELECT u.id, u.email, u.first_name, u.last_name, u.pseudo,
                   u.is_active, u.created_at
            FROM users u
            WHERE u.id = %s
              AND u.is_active = TRUE
              AND EXISTS (
                  SELECT 1 FROM sessions s
                  WHERE s.user_id = u.id
                    AND s.expires_at > NOW()
                  LIMIT 1
              )
            LIMIT 1; 
        """,(user_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close()
        conn.close()





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