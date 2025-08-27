from typing import Optional
from api.controller import permission_controller

def list_permissions(limit: int, offset: int, q: Optional[str]):
    rows = permission_controller.list_permissions(limit, offset, q)
    return [dict(id=r[0], code=r[1], label=r[2], description=r[3],
                 created_at=r[4], updated_at=r[5]) for r in rows]

def create_permission(code: str, label: str, description: Optional[str]):
    if permission_controller.get_permission_by_code(code):
        raise ValueError("Permission existe deja")
    pid = permission_controller.create_permission(code, label, description)
    return {"id": pid, "code": code, "label": label, "description": description}

def update_permission(code: str, label: Optional[str], description: Optional[str]):
    if not permission_controller.get_permission_by_code(code):
        raise ValueError("Permission onconue")
    permission_controller.update_permission(code, description, label)
    return {"message": "Permission mise a jour"}

def delete_permission(code: str):
    if not permission_controller.get_permission_by_code(code):
        raise ValueError("Permission inconnue")
    permission_controller.delete_permission(code)
    return {"message": "Permission supprimer"}