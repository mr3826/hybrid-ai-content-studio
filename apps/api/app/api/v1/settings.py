from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.settings import ConfigExport, ConfigImport, StudioStatusRead
from app.services import brand_service, niche_service, platform_service, settings_service

router = APIRouter(prefix="/settings", tags=["Studio Settings"])


@router.get("/status", response_model=StudioStatusRead)
async def get_status(session: AsyncSession = Depends(get_db)):
    """Check whether niche and brand are configured, and readiness of discovery/generation gates."""
    return await settings_service.get_studio_status(session)


@router.get("/export", response_model=ConfigExport)
async def export_studio_configuration(session: AsyncSession = Depends(get_db)):
    """Export complete Niche, Brand, Exemplars, and Platform settings."""
    return await settings_service.export_configuration(session)


@router.post("/import", response_model=StudioStatusRead)
async def import_studio_configuration(
    payload: ConfigImport,
    session: AsyncSession = Depends(get_db),
):
    """Import and apply Niche, Brand, Exemplars, and Platform settings."""
    return await settings_service.import_configuration(session, payload)


@router.post("/seed-all", response_model=StudioStatusRead)
async def seed_all_defaults(session: AsyncSession = Depends(get_db)):
    """Seed all initial example configurations (Niche, Brand, Platforms) for quick bootstrap."""
    await niche_service.seed_default_niche_if_empty(session)
    await brand_service.seed_default_brand_if_empty(session)
    await platform_service.seed_platforms_from_example(session)
    return await settings_service.get_studio_status(session)
