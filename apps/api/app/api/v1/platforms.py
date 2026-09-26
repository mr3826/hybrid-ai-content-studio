from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.platform import ALLOWED_PLATFORMS
from app.schemas.platform import PlatformSettingBase, PlatformSettingRead, PlatformSettingUpdate
from app.services import platform_service

router = APIRouter(prefix="/platforms", tags=["Platform Launchers"])


@router.get("", response_model=Dict[str, PlatformSettingRead])
async def get_platforms(session: AsyncSession = Depends(get_db)):
    """Fetch configuration for all 4 distribution platforms (YouTube, Facebook, Instagram, TikTok)."""
    return await platform_service.get_all_platforms(session)


@router.put("/{platform}", response_model=PlatformSettingRead)
async def update_platform_setting(
    platform: str,
    payload: PlatformSettingUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update URL and handle configuration for a specific platform.
    Enforces HTTPS URL validation.
    """
    platform_key = platform.lower()
    if platform_key not in ALLOWED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{platform}' is not supported. Allowed: {ALLOWED_PLATFORMS}",
        )
    try:
        return await platform_service.update_platform(session, platform_key, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/seed-default", response_model=Dict[str, PlatformSettingRead])
async def seed_default_platforms(session: AsyncSession = Depends(get_db)):
    """Seed platform settings from config/platforms.example.yaml."""
    return await platform_service.seed_platforms_from_example(session)
