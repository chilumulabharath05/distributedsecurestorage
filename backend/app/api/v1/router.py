"""API v1 Main Router"""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.files import router as files_router
from app.api.v1.endpoints.analytics import analytics_router, sharing_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(files_router)
api_router.include_router(analytics_router)
api_router.include_router(sharing_router)
