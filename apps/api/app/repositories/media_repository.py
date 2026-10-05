from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.media import MediaPackage, SceneVoiceTrack


class MediaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_package(self, package: MediaPackage) -> MediaPackage:
        self.session.add(package)
        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def get_package_by_id(self, package_id: str) -> Optional[MediaPackage]:
        stmt = (
            select(MediaPackage)
            .options(selectinload(MediaPackage.voice_tracks))
            .where(MediaPackage.id == package_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_package_by_script(self, script_id: str) -> Optional[MediaPackage]:
        stmt = (
            select(MediaPackage)
            .options(selectinload(MediaPackage.voice_tracks))
            .where(MediaPackage.script_id == script_id)
            .order_by(MediaPackage.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def update_package(self, package: MediaPackage) -> MediaPackage:
        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def delete_package(self, package_id: str) -> bool:
        stmt = delete(MediaPackage).where(MediaPackage.id == package_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount > 0

    async def add_voice_track(self, track: SceneVoiceTrack) -> SceneVoiceTrack:
        self.session.add(track)
        await self.session.commit()
        await self.session.refresh(track)
        return track

    async def list_voice_tracks(self, package_id: str) -> List[SceneVoiceTrack]:
        stmt = (
            select(SceneVoiceTrack)
            .where(SceneVoiceTrack.media_package_id == package_id)
            .order_by(SceneVoiceTrack.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def clear_voice_tracks(self, package_id: str) -> None:
        stmt = delete(SceneVoiceTrack).where(SceneVoiceTrack.media_package_id == package_id)
        await self.session.execute(stmt)
        await self.session.commit()
