from typing import Optional
from api.controller import permission_controller


def list_permissions(limit: int, offset: int, q: Optional[str]):
    rows, total = permission_controller.list_permissions(limit, offset, q)
    items = [
        dict(id=r[0], code=r[1], label=r[2], description=r[3],
             created_at=r[4], updated_at=r[5])
        for r in rows
    ]
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": total
    }

def list_permission_from_role(role_id: int):
    rows = permission_controller.list_permissions_by_role(role_id)
    return [
        {"code": r[0], "label": r[1], "description": r[2], "created_at": r[3], "updated_at": r[4]}
        for r in rows
    ]

def list_role_from_permission(perm_code: str):
    rows = permission_controller.list_role_by_permission(perm_code)
    return [{"id": r[0], "code": r[1], "label": r[2]} for r in rows]

def create_permission(code: str, label: str, description: Optional[str]):
    if permission_controller.get_permission_by_code(code):
        raise ValueError("La permission existe déjà.")
    pid = permission_controller.create_permission(code, label, description)
    return {"id": pid, "code": code, "label": label, "description": description}

def add_permission_to_role(role_id: int, perm_code: str):
    inserted = permission_controller.add_permission_to_role(role_id, perm_code)
    if inserted:
        return {"message": "Permission lie au role"}
    return {"message": "deja liée (aucune modification)"}

def update_permission(code: str, label: Optional[str], description: Optional[str]):
    if not permission_controller.get_permission_by_code(code):
        raise ValueError("Permission inconnue.")
    permission_controller.update_permission(code, label, description)
    return {"message": "Permission mise à jour."}

def delete_permission(code: str):
    if not permission_controller.get_permission_by_code(code):
        raise ValueError("Permission inconnue")
    permission_controller.delete_permission(code)
    return {"message": "Permission supprimer"}

def remove_permission_from_role(role_id: int, perm_code: str):
    deleted = permission_controller.remove_permission_from_role(role_id, perm_code)
    if deleted:
        return {"message": "Permission détachée du rôle."}
    return {"message": "Association introuvable (aucune modification)."}