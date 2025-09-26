from typing import Optional, Dict, Any
from api.controller import role_controller, permission_controller

def list_roles(limit: int, offset: int, q: Optional[str]):
    rows, total = role_controller.list_roles(limit, offset, q)  
    items = [
        dict(id=r[0], code=r[1], label=r[2], description=r[3], created_at=r[4], updated_at=r[5])
        for r in rows
    ]
    return {"items": items, "limit": limit, "offset": offset, "total": int(total)}

def get_role(role_id: int):
    r = role_controller.get_role_by_id(role_id)
    if not r : raise ValueError("Role introuvable")
    perms = permission_controller.list_permissions_by_role(role_id)
    return {
        "id": r[0], "code": r[1], "label": r[2], "description": r[3],
        "created_at": r[4], "updated_at": r[5],
        "permissions": [{"id": p[0], "code": p[1], "label": p[2], "description": p[3]} for p in perms]
    }

def create_role(code: str, label: str, description: Optional[str]):
    if role_controller.get_role_by_code(code):
        raise ValueError("Role existe deja")
    rid = role_controller.create_role(code, label, description)
    return {"id": rid, "code": code, "label": label, "description": description}

def update_role(role_id: int, label: Optional[str], description: Optional[str]):
    if not role_controller.get_role_by_id(role_id):
        raise ValueError("Role introuvable")
    role_controller.update_role(role_id, label, description)
    return {"message": "Role mis a jour "}

def delete_role(role_id: int):
    if not role_controller.get_role_by_id(role_id):
        raise ValueError(" Role introuvable")
    role_controller.delete_role(role_id)
    return {"message": "Role supprime"}

def add_permission(role_id: int, perm_code: str):
    r = role_controller.get_role_by_id(role_id)
    if not r: raise ValueError("Role introuvable")
    p = permission_controller.get_permission_by_code(perm_code)
    if not p: raise ValueError("Permission inconnue")
    role_controller.add_permission_to_role(role_id, p[0])
    return {"message": "Permission ajouter"}

def remove_permission(role_id: int, perm_code: str):
    r = role_controller.get_role_by_id(role_id)
    if not r: ValueError("Role introuvable")
    p = permission_controller.get_permission_by_code(perm_code)
    if not p : ValueError("Permission inconnue")
    role_controller.remove_permission_from_role(role_id, p[0])
    return {"message", "Permission retiree"}