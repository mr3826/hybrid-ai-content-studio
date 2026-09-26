from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.brand import BrandExemplarRead, BrandProfileRead
from app.schemas.niche import NicheProfileRead
from app.schemas.platform import PlatformSettingRead
from app.schemas.settings import ConfigExport, ConfigImport, StudioStatusRead
from app.services import brand_service, niche_service, platform_service


async def get_studio_status(session: AsyncSession) -> StudioStatusRead:
    niche = await niche_service.get_niche_profile(session)
    brand = await brand_service.get_brand_profile(session)
    platforms = await platform_service.get_all_platforms(session)

    niche_ok = niche is not None and bool(niche.name and niche.one_sentence_definition)
    brand_ok = brand is not None and bool(brand.brand_name and brand.tone)

    configured_platforms = sum(
        1 for p in platforms.values() if bool(p.channel_url or p.publishing_url)
    )

    setup_done = niche_ok and brand_ok

    return StudioStatusRead(
        niche_configured=niche_ok,
        brand_configured=brand_ok,
        platforms_configured_count=configured_platforms,
        is_setup_completed=setup_done,
        discovery_ready=niche_ok,
        generation_ready=setup_done,
        active_niche_name=niche.name if niche else None,
        active_brand_name=brand.brand_name if brand else None,
    )


async def export_configuration(session: AsyncSession) -> ConfigExport:
    niche = await niche_service.get_niche_profile(session)
    brand = await brand_service.get_brand_profile(session)
    exemplars = await brand_service.list_exemplars(session)
    platforms = await platform_service.get_all_platforms(session)

    return ConfigExport(
        exported_at=datetime.now(timezone.utc),
        studio_version="0.1.0",
        niche=NicheProfileRead.model_validate(niche) if niche else None,
        brand=BrandProfileRead.model_validate(brand) if brand else None,
        exemplars=[BrandExemplarRead.model_validate(e) for e in exemplars],
        platforms={
            k: PlatformSettingRead.model_validate(v) for k, v in platforms.items()
        },
    )


async def import_configuration(
    session: AsyncSession, data: ConfigImport
) -> StudioStatusRead:
    if data.niche:
        await niche_service.upsert_niche_profile(session, data.niche)

    if data.brand:
        await brand_service.upsert_brand_profile(session, data.brand)

    if data.exemplars:
        for ex in data.exemplars:
            await brand_service.create_exemplar(session, ex)

    if data.platforms:
        for plat_name, plat_data in data.platforms.items():
            await platform_service.update_platform(session, plat_name, plat_data)

    return await get_studio_status(session)
