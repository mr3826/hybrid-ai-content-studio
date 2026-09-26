from pathlib import Path
from typing import List, Optional
import yaml
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import (
    BrandExemplar,
    BrandProfile,
    SINGLETON_BRAND_ID,
)
from app.schemas.brand import (
    BrandExemplarBase,
    BrandExemplarCreate,
    BrandProfileBase,
    BrandProfileCreate,
    BrandProfileUpdate,
)


async def get_brand_profile(session: AsyncSession) -> Optional[BrandProfile]:
    stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_brand_profile(
    session: AsyncSession, data: BrandProfileBase
) -> BrandProfile:
    """Save or update the single brand profile.
    Enforces the single-brand invariant: exactly one primary brand profile.
    """
    profile = await get_brand_profile(session)
    data_dict = data.model_dump()

    if profile is None:
        profile = BrandProfile(id=SINGLETON_BRAND_ID, **data_dict)
        session.add(profile)
    else:
        for k, v in data_dict.items():
            setattr(profile, k, v)

    await session.commit()
    await session.refresh(profile)
    return profile


async def seed_default_brand_if_empty(session: AsyncSession) -> Optional[BrandProfile]:
    existing = await get_brand_profile(session)
    if existing:
        return existing

    example_path = Path("config/brand.example.yaml")
    if example_path.exists():
        with open(example_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
            base = BrandProfileBase(**raw)
            return await upsert_brand_profile(session, base)
    return None


async def list_exemplars(
    session: AsyncSession, category: Optional[str] = None
) -> List[BrandExemplar]:
    stmt = select(BrandExemplar)
    if category:
        stmt = stmt.where(BrandExemplar.category == category)
    stmt = stmt.order_by(BrandExemplar.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_exemplar(
    session: AsyncSession, data: BrandExemplarBase
) -> BrandExemplar:
    exemplar = BrandExemplar(**data.model_dump())
    session.add(exemplar)
    await session.commit()
    await session.refresh(exemplar)
    return exemplar


async def delete_exemplar(session: AsyncSession, exemplar_id: str) -> bool:
    stmt = select(BrandExemplar).where(BrandExemplar.id == exemplar_id)
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return False
    await session.delete(item)
    await session.commit()
    return True
