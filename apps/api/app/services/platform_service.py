from pathlib import Path
from typing import Dict, List
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import ALLOWED_PLATFORMS, PlatformSetting
from app.schemas.platform import PlatformSettingBase, PlatformSettingUpdate

DEFAULT_PLATFORM_URLS = {
    "youtube": {
        "channel_name": "My Channel",
        "channel_url": "",
        "publishing_url": "https://studio.youtube.com/",
        "account_handle": "",
    },
    "facebook": {
        "channel_name": "My Page",
        "channel_url": "",
        "publishing_url": "https://business.facebook.com/creatorstudio",
        "account_handle": "",
    },
    "instagram": {
        "channel_name": "My Profile",
        "channel_url": "",
        "publishing_url": "https://www.instagram.com/",
        "account_handle": "",
    },
    "tiktok": {
        "channel_name": "My TikTok",
        "channel_url": "",
        "publishing_url": "https://www.tiktok.com/upload",
        "account_handle": "",
    },
}


async def get_all_platforms(session: AsyncSession) -> Dict[str, PlatformSetting]:
    stmt = select(PlatformSetting)
    result = await session.execute(stmt)
    existing = {p.platform: p for p in result.scalars().all()}

    # Initialize any missing platform records with defaults
    changed = False
    for p_name in ALLOWED_PLATFORMS:
        if p_name not in existing:
            default_data = DEFAULT_PLATFORM_URLS.get(p_name, {})
            new_plat = PlatformSetting(
                platform=p_name,
                channel_name=default_data.get("channel_name", ""),
                channel_url=default_data.get("channel_url", ""),
                publishing_url=default_data.get("publishing_url", ""),
                account_handle=default_data.get("account_handle", ""),
                is_active=True,
            )
            session.add(new_plat)
            existing[p_name] = new_plat
            changed = True

    if changed:
        await session.commit()
        for p in existing.values():
            await session.refresh(p)

    return existing


async def update_platform(
    session: AsyncSession, platform: str, data: PlatformSettingBase
) -> PlatformSetting:
    if platform not in ALLOWED_PLATFORMS:
        raise ValueError(f"Platform '{platform}' not in allowed platforms: {ALLOWED_PLATFORMS}")

    platforms = await get_all_platforms(session)
    target = platforms[platform]

    target.channel_name = data.channel_name
    target.channel_url = data.channel_url
    target.publishing_url = data.publishing_url
    target.account_handle = data.account_handle
    target.is_active = data.is_active

    await session.commit()
    await session.refresh(target)
    return target


async def seed_platforms_from_example(session: AsyncSession) -> Dict[str, PlatformSetting]:
    example_path = Path("config/platforms.example.yaml")
    if example_path.exists():
        with open(example_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
            platforms = await get_all_platforms(session)
            for p_name, p_data in raw.items():
                if p_name in platforms:
                    target = platforms[p_name]
                    target.channel_name = p_data.get("channel_name", target.channel_name)
                    target.channel_url = p_data.get("channel_url", target.channel_url)
                    target.publishing_url = p_data.get("studio_url", p_data.get("publishing_url", target.publishing_url))
                    target.account_handle = p_data.get("account_name", target.account_handle)
            await session.commit()
    return await get_all_platforms(session)
