from typing import Optional, Dict, Tuple, List
from api.controller import category_controller as repo
from schema.category import CategoryIn, CategoryUpdate

def create_category(payload: CategoryIn) -> Dict:
    if repo.get_category_by_code(payload.code):
        raise ValueError("ce code de categories existe deja")
    data = payload.model_dump()
    return repo.insert_category(data)

def get_category(cid: int) -> Dict:
    cat = repo.get_category_by_id(cid)
    if not cat: 
        return ValueError("Categorie introuvable")
    return cat

def list_categories(search: Optional[str], limit: int, offset: int) -> Tuple[int, List[Dict]]:
    return repo.list_categories(search, limit, offset)

def update_category(cid: int, payload: CategoryUpdate) -> Dict:
    if payload.model_dump(exclude_unset=True) == {}:
        return get_category(cid)
    updated = repo.update_category(cid, payload.model_dump(exclude_unset=True))
    if not updated:
        raise ValueError("Catégorie introuvable.")
    return updated

def delete_category(cid: int) -> None:
    if not repo.delete_category(cid):
        raise ValueError("Catégorie introuvable.")