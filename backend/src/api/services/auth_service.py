# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, verify_access_token
from api.controller import auth_controller, user_controller
from utils.crypto import sha256_hex

ACCESS_TOKEN_EXPIRE_MINUTES = 60  


def register(email: str, password: str, first_name: str = "", last_name: str = "") -> Dict[str, Any]:
    existing = auth_controller.find_user_by_email(email)
    if existing:
        raise ValueError("Email deja utilise")
    pw_hash = hash_password(password)
    user_id = auth_controller.insert_user(email, pw_hash, first_name, last_name)
    return {"user_id": user_id, "message": "Utilisateur cree"}


def login(email: str, password: str) -> Dict[str, Any]:
    user = auth_controller.find_user_by_email(email)
    if not user:
        raise ValueError("Identifiants invalides")
    uid, uemail, pw_hash, is_active = user
    if not is_active:
        raise ValueError("Compte desactive")
    if not verify_password(password, pw_hash):
        raise ValueError("Identifiants invalides")

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": uemail, "user_id": uid}, expires_delta=expires)

    payload = verify_access_token(token) or {}
    exp_ts = payload.get("exp") if payload else None
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else None
    auth_controller.add_session(uid, sha256_hex(token), exp_dt)

    return {"access_token": token, "token_type": "Bearer", "expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES}


def logout(token: str) -> Dict[str, str]:
    sess = auth_controller.get_session_by_token(token)
    if not sess:
        return {"message": "Deconnexion effectuee"}
    auth_controller.delete_session_by_token(token)
    return {"message": "Deconnexion effectuee"}


def get_user_connected(token: str) -> Dict[str, Any]:
    payload = verify_access_token(token)
    if not payload:
        raise ValueError("Token invalide ou expire")
    # Vérifie que la session existe toujours (non révoquée)
    if not auth_controller.get_session_by_token(sha256_hex(token)):
        raise ValueError("Session expiree ou deconnectee")

    uid = int(payload["user_id"])
    row = user_controller.get_user_by_id(uid)
    if not row:
        raise ValueError("Utilisateur introuvable")
    return {"id": row[0], "email": row[1], "first_name": row[2], "last_name": row[3], "is_active": row[4]}