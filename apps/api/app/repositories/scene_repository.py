from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc, asc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scene import Scene, MediaAsset
from app.repositories.base import BaseRepository


class SceneRepository(BaseRepository[Scene]):
    """Data access repository for Storyboard Scene entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_scene(self, scene: Scene) -> Scene:
        self.session.add(scene)
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def create_batch(self, scenes: List[Scene]) -> List[Scene]:
        for s in scenes:
            self.session.add(s)
        await self.session.commit()
        for s in scenes:
            await self.session.refresh(s)
        return scenes

    async def get_scene_by_id(self, scene_id: str) -> Optional[Scene]:
        stmt = (
            select(Scene)
            .options(selectinload(Scene.asset_rights))
            .where(Scene.id == scene_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_scenes_by_script(self, script_id: str) -> List[Scene]:
        stmt = (
            select(Scene)
            .options(selectinload(Scene.asset_rights))
            .where(Scene.script_id == script_id)
            .order_by(asc(Scene.scene_order))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_scene(self, scene: Scene) -> Scene:
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def delete_scene(self, scene_id: str) -> bool:
        scene = await self.get_scene_by_id(scene_id)
        if not scene:
            return False
        await self.session.delete(scene)
        await self.session.commit()
        return True

    async def delete_scenes_by_script(self, script_id: str) -> int:
        stmt = delete(Scene).where(Scene.script_id == script_id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.rowcount or 0

    async def reorder_scenes(self, script_id: str, scene_order_ids: List[str]) -> List[Scene]:
        scenes = await self.list_scenes_by_script(script_id)
        scene_map = {s.id: s for s in scenes}
        for index, s_id in enumerate(scene_order_ids, start=1):
            if s_id in scene_map:
                scene_map[s_id].scene_order = index
        await self.session.commit()
        return await self.list_scenes_by_script(script_id)


class MediaAssetRepository(BaseRepository[MediaAsset]):
    """Data access repository for MediaAsset entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_asset(self, asset: MediaAsset) -> MediaAsset:
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def get_asset_by_id(self, asset_id: str) -> Optional[MediaAsset]:
        stmt = (
            select(MediaAsset)
            .options(selectinload(MediaAsset.asset_rights))
            .where(MediaAsset.id == asset_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_assets(
        self,
        asset_type: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 100,
    ) -> List[MediaAsset]:
        stmt = select(MediaAsset).options(selectinload(MediaAsset.asset_rights))
        if asset_type and asset_type != "all":
            stmt = stmt.where(MediaAsset.asset_type == asset_type)
        if query:
            stmt = stmt.where(MediaAsset.name.ilike(f"%{query}%"))
        stmt = stmt.order_by(desc(MediaAsset.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete_asset(self, asset_id: str) -> bool:
        asset = await self.get_asset_by_id(asset_id)
        if not asset:
            return False
        await self.session.delete(asset)
        await self.session.commit()
        return True
