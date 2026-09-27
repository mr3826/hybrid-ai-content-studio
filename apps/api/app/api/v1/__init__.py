from fastapi import APIRouter
from app.api.v1.brand import router as brand_router
from app.api.v1.engines import router as engines_router
from app.api.v1.health import router as health_router
from app.api.v1.niche import router as niche_router
from app.api.v1.niche_guard import router as niche_guard_router
from app.api.v1.brand_qa import router as brand_qa_router
from app.api.v1.platforms import router as platforms_router
from app.api.v1.settings import router as settings_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.rss import router as rss_router
from app.api.v1.trends import router as trends_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.research import router as research_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.ai import router as ai_router
from app.api.v1.originality import router as originality_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(niche_router)
api_v1_router.include_router(brand_router)
api_v1_router.include_router(platforms_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(engines_router)
api_v1_router.include_router(niche_guard_router)
api_v1_router.include_router(brand_qa_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(rss_router)
api_v1_router.include_router(trends_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(research_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(originality_router)


