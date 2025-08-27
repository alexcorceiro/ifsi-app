# -*- coding: utf-8 -*-
import os
import psycopg2
from psycopg2 import pool
from core import config

_DB_POOL: pool.SimpleConnectionPool | None = None

def init_db_pool(minconn: int = 1, maxconn: int = 10) -> None:
    """
    Initialise le pool (à appeler dans l'événement startup).
    Force UTF-8 et messages serveur en ASCII pour éviter les erreurs d'encodage.
    """
    global _DB_POOL
    if _DB_POOL is not None:
        return  # déjà prêt

    os.environ["PGCLIENTENCODING"] = "UTF8"
    options = "-c client_encoding=UTF8 -c lc_messages=C"

    try:
        _DB_POOL = pool.SimpleConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=config.DB_HOST,  
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            options=options,
        )
        conn = _DB_POOL.getconn()
        try:
            conn.set_client_encoding("UTF8")
            with conn.cursor() as cur:
                cur.execute("SET lc_messages = 'C';")
        finally:
            _DB_POOL.putconn(conn)

    except Exception as e:
        print("[DB-INIT-ERROR]", repr(e))
        raise RuntimeError("DB init failed")

def get_db_connection():
    """
    Récupère une connexion depuis le pool (UTF-8 + lc_messages=C).
    """
    if _DB_POOL is None:
        raise RuntimeError("DB not ready")
    conn = _DB_POOL.getconn()
    try:
        conn.set_client_encoding("UTF8")
        with conn.cursor() as cur:
            cur.execute("SET lc_messages = 'C';")
    except Exception:
        _DB_POOL.putconn(conn)
        raise
    return conn

def release_db_connection(conn) -> None:
    """
    Remet la connexion dans le pool.
    """
    if _DB_POOL and conn:
        _DB_POOL.putconn(conn)

def close_db_pool() -> None:
    """
    Ferme toutes les connexions (à appeler dans l'événement shutdown).
    """
    global _DB_POOL
    if _DB_POOL:
        _DB_POOL.closeall()
        _DB_POOL = None

def ping_db() -> bool:
    """
    Test léger de santé DB. Retourne True si SELECT 1 passe.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True
    finally:
        release_db_connection(conn)
