# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from argon2 import PasswordHasher
from utils.password import hash_password, verify_password
from utils.jwt import create_access_token, verify_access_token, create_refresh_token , hash_token
from api.controller import auth_controller, user_controller
from utils.crypto import sha256_hex
from schema.auth import RegisterIn, LoginIn , UserOut, TokensOut, AuthOut
from fastapi import HTTPException


ACCESS_TOKEN_EXPIRE_MINUTES = 60  

ph=PasswordHasher()

def register(payload: RegisterIn) -> UserOut:
    
    existing = auth_controller.find_user_by_email(payload.email)
    if existing:
        raise ValueError("Email déjà utilisé")

    password_hash = hash_password(payload.password)

    data = payload.model_dump()
    data["password_hash"] = password_hash
    data.pop("password")   

    user = auth_controller.insert_user(data)

    return UserOut(
        id=user["id"],
        email=user["email"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        pseudo=user.get("pseudo"),
        phone_number=user.get("phone_number"),
        city=user.get("city"),
        country=user.get("country"),
        is_active=user.get("is_active"),
        created_at=user.get("created_at"),
    )

def login(payload: LoginIn) -> AuthOut: 
   u = user_controller.get_user_by_email(payload.email)
   if not u or not u["is_active"]:
       raise HTTPException(status_code=400, detail="Identifiants invalides")
   
   try: 
       ph.verify(u["password_hash"], payload.password)
   except Exception:
       raise HTTPException(status_code=400, detail="Identifiants invalides")
   
   access = create_access_token({"user_id": u["id"], "email": u["email"]})
   refresh = create_refresh_token({"user_id": u["id"]}, days=15)

   exp = datetime.now(timezone.utc) + timedelta(days=15)
   sid = auth_controller.add_session(u["id"], sha256_hex(refresh), exp)

   if not sid :
       raise HTTPException(status_code=500, detail="Impossible de cree une session")
   
   print(f"[LOGIN] OK: session_id={sid}, user_id={u['id']}")
   
   user = UserOut(
                id=u["id"], email=u["email"], first_name=u["first_name"],
                last_name=u["last_name"], pseudo=u["pseudo"], is_active=u["is_active"]
            )

   return AuthOut(
        user=user,
        tokens=TokensOut(
            access_token=access,
            refresh_token=refresh
        )
    )

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
    uid = int(payload["user_id"])

    sess = auth_controller.get_active_session_by_user_id(uid)
    if not sess : 
        raise ValueError("Session expiree ou deconnectee")
    
    user = user_controller.get_roles_by_user_id(uid)
    if not user:
        raise ValueError("Utilisateur introuvable")
    
    return{
        "id": user["id"],
        "email": user["email"],
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "pseudo": user.get("pseudo"),
        "is_active": user["is_active"],
        "created_at": user.get("created_at"),
    }

def me_from_access_token(access_token: str) -> Dict[str, Any]:
    payload = verify_access_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    uid = payload.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="Token incomplet")

    me = auth_controller.fetch_me_if_session_active(int(uid))
    if not me:
        raise HTTPException(status_code=401, detail="Session expirée ou déconnectée")

    return me




