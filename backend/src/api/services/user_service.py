from typing import Dict, List, Optional, Any , Iterable
from api.controller import user_controller

def _row_to_user(row: Optional[tuple]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    return {
        "id": row[0],
        "email": row[1],
        "first_name": row[2],
        "last_name": row[3],
        "is_active": row[4],
    }

def get_user_by_id(user_id: int) -> Dict[str, Any]:
    row = user_controller.get_user_by_id(user_id)
    user = _row_to_user(row)
    if not user : 
        raise ValueError("Utilisateur introuvable")
    return user 

def get_all_users(limit = 100, offset: int = 0) -> List[Dict[str, Any]]:
    rows = user_controller.get_all_users()
    users = [_row_to_user(r) for r in rows]
    return users[offset: offset + limit]

def has_any_role(user_id: int, roles: List[str]) -> bool:
    # si tu as déjà une fonction get_roles_by_user_id, sinon à implémenter
    from api.controller import role_controller
    user_roles = set(role_controller.get_roles_codes_by_user_id(user_id) or [])
    return any(r in user_roles for r in roles)

def has_all_roles(user_id: int, required_roles: List[str]) -> bool:
    if not required_roles:
        return True
    user_roles = set(user_controller.get_roles_by_user_id(user_id) or [])
    return set(required_roles).issubset(user_roles)

def has_permissions(user_id: int, required: List[str]) -> bool:
    """Vérifie que l’utilisateur possède TOUTES les permissions demandées."""
    user_perms = set(user_controller.get_permissions_by_user_id(user_id) or [])
    return all(p in user_perms for p in required)
    

def update_user(user_id: int, first_name: str, last_name: str) -> Dict[str, str]:
    if len(first_name) > 100 or len(last_name) > 100:
        raise ValueError("Champs trop longs (max 100)")
    user_controller.update_user_basic(user_id, first_name, last_name)
    return {"message": "Utilisateur mis à jour"}

def delete_user(user_id: int) -> Dict[str, str]:
    row = user_controller.get_user_by_id(user_id)
    if not row:
        raise ValueError("Utilisateur introuvable")
    user_controller.delete_user(user_id)
    return {"message": "Utilisateur supprimé"}