from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content_family import ContentItem
from app.models.export import PlatformPublication
from app.repositories.base import BaseRepository


class PublishingRepository(BaseRepository[PlatformPublication]):
    """Data access repository for PlatformPublication tracking and state transitions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, publication: PlatformPublication) -> PlatformPublication:
        self.session.add(publication)
        await self.session.commit()
        await self.session.refresh(publication)
        return publication

    async def get_by_id(self, pub_id: str) -> Optional[PlatformPublication]:
        stmt = (
            select(PlatformPublication)
            .where(PlatformPublication.id == pub_id)
            .options(
                selectinload(PlatformPublication.content_item),
                selectinload(PlatformPublication.export_package),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_item_id(self, item_id: str) -> List[PlatformPublication]:
        stmt = (
            select(PlatformPublication)
            .where(PlatformPublication.content_item_id == item_id)
            .order_by(PlatformPublication.platform)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_item_and_platform(self, item_id: str, platform: str) -> Optional[PlatformPublication]:
        stmt = (
            select(PlatformPublication)
            .where(
                PlatformPublication.content_item_id == item_id,
                PlatformPublication.platform == platform,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[PlatformPublication]:
        stmt = select(PlatformPublication).order_by(desc(PlatformPublication.updated_at))
        if status:
            stmt = stmt.where(PlatformPublication.status == status)
        if platform:
            stmt = stmt.where(PlatformPublication.platform == platform)
        stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update(
        self,
        pub_id: str,
        updates: Dict[str, Any],
    ) -> Optional[PlatformPublication]:
        pub = await self.get_by_id(pub_id)
        if not pub:
            return None

        for field, value in updates.items():
            if hasattr(pub, field):
                setattr(pub, field, value)

        pub.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(pub)

        # Sync parent item publication status
        await self.sync_item_status(pub.content_item_id)
        return pub

    async def sync_item_status(self, item_id: str) -> Optional[str]:
        """Evaluates all platform publication states for an item and updates ContentItem.status."""
        item_stmt = select(ContentItem).where(ContentItem.id == item_id)
        item_res = await self.session.execute(item_stmt)
        item = item_res.scalar_one_or_none()
        if not item:
            return None

        pubs = await self.get_by_item_id(item_id)
        if not pubs:
            return item.status

        statuses = [p.status for p in pubs]
        has_published = any(s == "PUBLISHED" for s in statuses)
        all_resolved = all(s in ("PUBLISHED", "SKIPPED") for s in statuses)
        all_ready = all(s in ("READY", "PUBLISHED", "SKIPPED") for s in statuses)

        if has_published and all_resolved:
            new_status = "PUBLISHED"
        elif has_published:
            new_status = "PARTIALLY_PUBLISHED"
        elif all_ready:
            new_status = "READY_TO_PUBLISH"
        else:
            new_status = "EXPORTED"

        item.status = new_status
        item.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return new_status
