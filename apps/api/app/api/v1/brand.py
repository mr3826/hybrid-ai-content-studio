from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.brand import (
    BrandExemplarBase,
    BrandExemplarCreate,
    BrandExemplarRead,
    BrandMemoryBase,
    BrandMemoryCreate,
    BrandMemoryRead,
    BrandProfileBase,
    BrandProfileRead,
    BrandProfileUpdate,
)
from app.services import brand_service

router = APIRouter(prefix="/brand", tags=["Single Brand"])


@router.get("", response_model=BrandProfileRead)
async def get_active_brand(session: AsyncSession = Depends(get_db)):
    """Fetch the active single brand profile."""
    profile = await brand_service.get_brand_profile(session)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BrandProfile has not been configured yet. Initial setup required.",
        )
    return profile


@router.put("", response_model=BrandProfileRead)
async def update_active_brand(
    payload: BrandProfileUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Save or update the single active brand profile.
    Enforces the single-brand invariant: only one active brand profile exists.
    """
    profile = await brand_service.upsert_brand_profile(session, payload)
    return profile


@router.post("/seed-default", response_model=BrandProfileRead)
async def seed_default_brand(session: AsyncSession = Depends(get_db)):
    """Seed the default brand profile from config/brand.example.yaml."""
    profile = await brand_service.seed_default_brand_if_empty(session)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not seed default brand profile.",
        )
    return profile


@router.get("/exemplars", response_model=List[BrandExemplarRead])
async def list_brand_exemplars(
    category: Optional[str] = Query(None, description="Filter by exemplar category"),
    session: AsyncSession = Depends(get_db),
):
    """List approved brand exemplars (hooks, scripts, captions, do/don't examples)."""
    return await brand_service.list_exemplars(session, category=category)


@router.post(
    "/exemplars",
    response_model=BrandExemplarRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_exemplar(
    payload: BrandExemplarCreate,
    session: AsyncSession = Depends(get_db),
):
    """Add a new brand exemplar."""
    return await brand_service.create_exemplar(session, payload)


@router.delete("/exemplars/{exemplar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_exemplar(
    exemplar_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete a brand exemplar by ID."""
    deleted = await brand_service.delete_exemplar(session, exemplar_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exemplar '{exemplar_id}' not found.",
        )


@router.get("/memory", response_model=List[BrandMemoryRead])
async def list_brand_memory(
    memory_type: Optional[str] = Query(None, description="Filter by memory type (hook, cta, topic, etc.)"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    """List persistent brand memory items ordered by recent usage."""
    return await brand_service.list_brand_memory(session, memory_type=memory_type, limit=limit)


@router.post(
    "/memory",
    response_model=BrandMemoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_brand_memory(
    payload: BrandMemoryCreate,
    session: AsyncSession = Depends(get_db),
):
    """Record a brand memory item or increment usage count."""
    return await brand_service.record_brand_memory_item(session, payload)


@router.delete("/memory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand_memory(
    item_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Delete a brand memory item by ID."""
    deleted = await brand_service.delete_brand_memory_item(session, item_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand memory item '{item_id}' not found.",
        )

