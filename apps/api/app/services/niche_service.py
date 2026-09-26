from pathlib import Path
from typing import Optional
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.schemas.niche import NicheProfileBase, NicheProfileCreate, NicheProfileUpdate


async def get_niche_profile(session: AsyncSession) -> Optional[NicheProfile]:
    stmt = select(NicheProfile).where(NicheProfile.id == SINGLETON_NICHE_ID)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_niche_profile(
    session: AsyncSession, data: NicheProfileBase
) -> NicheProfile:
    """Save or update the single niche profile.
    Enforces the single-niche invariant: exactly one primary profile.
    """
    profile = await get_niche_profile(session)
    data_dict = data.model_dump()

    # Convert content_pillars models to dict if needed
    if "content_pillars" in data_dict and data_dict["content_pillars"]:
        data_dict["content_pillars"] = [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in data.content_pillars
        ]

    if profile is None:
        profile = NicheProfile(id=SINGLETON_NICHE_ID, **data_dict)
        session.add(profile)
    else:
        for k, v in data_dict.items():
            setattr(profile, k, v)

    await session.commit()
    await session.refresh(profile)
    return profile


async def seed_default_niche_if_empty(session: AsyncSession) -> Optional[NicheProfile]:
    existing = await get_niche_profile(session)
    if existing:
        return existing

    example_path = Path("config/niche.example.yaml")
    if example_path.exists():
        with open(example_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
            # Remove id if present so schema parses cleanly
            raw.pop("id", None)
            base = NicheProfileBase(**raw)
            return await upsert_niche_profile(session, base)
    return None
