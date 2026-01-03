# -*- coding: utf-8 -*-
from typing import Optional, List
from fastapi import Header, HTTPException
from utils.jwt import verify_access_token
from api.services import user_service


def require_bearer(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    return payload


def extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not isinstance(authorization, str):
        raise HTTPException(status_code=401, detail="Authorization manquant")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Format Bearer invalide")
    return parts[1]

def require_permissions(perms: List[str]):
    def _dep(authorization: Optional[str] = Header(default=None)) -> int:
        payload = require_bearer(authorization)
        uid = int(payload["user_id"])
        if not user_service.has_permissions(uid, perms):
            raise HTTPException(status_code=403, detail=f"Acces refuse (permission): {perms}")
        return uid
    return _dep


def require_any_role(roles: List[str]):
   
    def _dep(authorization: Optional[str] = Header(default=None)) -> int:
        payload = require_bearer(authorization)
        uid = int(payload["user_id"])
        if not user_service.has_any_role(uid, roles):
            raise HTTPException(status_code=403, detail=f"Acces refuse (role): {roles}")
        return uid
    return _dep


# Alias pour compatibilité avec les anciens imports
require_roles = require_any_role


def require_perms_and_roles(perms: List[str] = None, roles: List[str] = None):
    """
    Exige TOUTES les permissions ET/OU AU MOINS UN rôle.
    - Si 'perms' fourni -> toutes ces permissions.
    - Si 'roles' fourni -> au moins un de ces rôles.
    - Si les deux: il faut satisfaire les deux conditions.
    """
    perms = perms or []
    roles = roles or []

    def _dep(authorization: Optional[str] = Header(default=None)) -> int:
        payload = require_bearer(authorization)
        uid = int(payload["user_id"])
        if perms and not user_service.has_permissions(uid, perms):
            raise HTTPException(status_code=403, detail=f"Acces refuse (permission): {perms}")
        if roles and not user_service.has_any_role(uid, roles):
            raise HTTPException(status_code=403, detail=f"Acces refuse (role): {roles}")
        return uid

    return _dep



