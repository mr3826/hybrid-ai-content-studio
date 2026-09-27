from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import yaml
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import (
    BrandExemplar,
    BrandMemoryItem,
    BrandProfile,
    SINGLETON_BRAND_ID,
)
from app.schemas.brand import (
    BrandExemplarBase,
    BrandExemplarCreate,
    BrandMemoryBase,
    BrandMemoryCreate,
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


async def list_brand_memory(
    session: AsyncSession,
    memory_type: Optional[str] = None,
    limit: int = 50,
) -> List[BrandMemoryItem]:
    """Retrieve brand memory items ordered by recent usage."""
    stmt = select(BrandMemoryItem)
    if memory_type:
        stmt = stmt.where(BrandMemoryItem.memory_type == memory_type)
    stmt = stmt.order_by(BrandMemoryItem.last_used_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def record_brand_memory_item(
    session: AsyncSession,
    data: BrandMemoryBase,
) -> BrandMemoryItem:
    """Record a memory item (hook, CTA, topic, etc.) or increment usage if existing."""
    stmt = (
        select(BrandMemoryItem)
        .where(BrandMemoryItem.memory_type == data.memory_type)
        .where(BrandMemoryItem.content == data.content.strip())
    )
    res = await session.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.usage_count += 1
        existing.last_used_at = datetime.now(timezone.utc)
        if data.context_note:
            existing.context_note = data.context_note
        await session.commit()
        await session.refresh(existing)
        return existing

    item = BrandMemoryItem(
        memory_type=data.memory_type,
        content=data.content.strip(),
        context_note=data.context_note,
        usage_count=data.usage_count,
        last_used_at=datetime.now(timezone.utc),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_brand_memory_item(
    session: AsyncSession,
    item_id: str,
) -> bool:
    stmt = select(BrandMemoryItem).where(BrandMemoryItem.id == item_id)
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return False
    await session.delete(item)
    await session.commit()
    return True

