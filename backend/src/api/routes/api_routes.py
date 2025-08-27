from fastapi import APIRouter
from api.routes import auth_router, user_router, roles_router, permissions_router   # ✅ ici on précise le chemin complet

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(roles_router.router)
api_router.include_router(permissions_router.router)
