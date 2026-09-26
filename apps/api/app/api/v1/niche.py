from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.niche import NicheProfileBase, NicheProfileRead, NicheProfileUpdate
from app.services import niche_service

router = APIRouter(prefix="/niche", tags=["Single Niche"])


@router.get("", response_model=NicheProfileRead)
async def get_active_niche(session: AsyncSession = Depends(get_db)):
    """Fetch the active single niche profile."""
    profile = await niche_service.get_niche_profile(session)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NicheProfile has not been configured yet. Initial setup required.",
        )
    return profile


@router.put("", response_model=NicheProfileRead)
async def update_active_niche(
    payload: NicheProfileUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Save or update the single active niche profile.
    Enforces the single-niche invariant: only one active niche profile exists.
    """
    profile = await niche_service.upsert_niche_profile(session, payload)
    return profile


@router.post("/seed-default", response_model=NicheProfileRead)
async def seed_default_niche(session: AsyncSession = Depends(get_db)):
    """Seed the default niche profile from config/niche.example.yaml."""
    profile = await niche_service.seed_default_niche_if_empty(session)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not seed default niche profile.",
        )
    return profile
