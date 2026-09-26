from fastapi import APIRouter
from app.api.v1.brand import router as brand_router
from app.api.v1.engines import router as engines_router
from app.api.v1.health import router as health_router
from app.api.v1.niche import router as niche_router
from app.api.v1.platforms import router as platforms_router
from app.api.v1.settings import router as settings_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(niche_router)
api_v1_router.include_router(brand_router)
api_v1_router.include_router(platforms_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(engines_router)
