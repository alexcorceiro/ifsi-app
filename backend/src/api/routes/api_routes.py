from fastapi import APIRouter
from api.routes import (auth_router, user_router, roles_router, permissions_router, protocols_router, categories_routes, protocols_router, lesson_routes, 
                        course_routes, programs_router, ue_router, dose_routes, training_routes, case_routes)

api_router = APIRouter()
api_router.include_router(auth_router.router)
api_router.include_router(user_router.router)
api_router.include_router(roles_router.router)
api_router.include_router(permissions_router.router)
api_router.include_router(protocols_router.router)
api_router.include_router(categories_routes.router)
api_router.include_router(lesson_routes.router)
api_router.include_router(course_routes.router)
api_router.include_router(programs_router.router)
api_router.include_router(ue_router.router)
api_router.include_router(dose_routes.router)
api_router.include_router(training_routes.router)
api_router.include_router(case_routes.router)