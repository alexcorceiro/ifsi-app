from fastapi import APIRouter
from api.routes import auth_router, user_router, roles_router, permissions_router, protocols_router, categories_routes, protocols_router

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(roles_router.router)
api_router.include_router(permissions_router.router)
api_router.include_router(protocols_router.router)
api_router.include_router(categories_routes.router)
