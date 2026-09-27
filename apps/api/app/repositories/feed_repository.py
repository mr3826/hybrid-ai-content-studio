from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rss import RssFeed
from app.repositories.base import BaseRepository


class FeedRepository(BaseRepository[RssFeed]):
    """Storage boundary for RSS/Atom discovery feed sources."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, feed_id: str) -> Optional[RssFeed]:
        stmt = select(RssFeed).where(RssFeed.id == feed_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_feeds(self, enabled_only: bool = False) -> List[RssFeed]:
        stmt = select(RssFeed).order_by(RssFeed.name.asc())
        if enabled_only:
            stmt = stmt.where(RssFeed.enabled.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_feed_by_url(self, url: str) -> Optional[RssFeed]:
        stmt = select(RssFeed).where(RssFeed.url == url)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_feed(self, data: Dict[str, Any]) -> RssFeed:
        feed = RssFeed(**data)
        self.session.add(feed)
        await self.session.commit()
        await self.session.refresh(feed)
        return feed

    async def update_feed(self, feed_id: str, data: Dict[str, Any]) -> Optional[RssFeed]:
        feed = await self.get_by_id(feed_id)
        if not feed:
            return None
        for key, value in data.items():
            if hasattr(feed, key) and key != "id":
                setattr(feed, key, value)
        await self.session.commit()
        await self.session.refresh(feed)
        return feed

    async def delete_feed(self, feed_id: str) -> bool:
        feed = await self.get_by_id(feed_id)
        if not feed:
            return False
        await self.session.delete(feed)
        await self.session.commit()
        return True

    async def record_status(
        self, feed_id: str, success: bool, error: Optional[str] = None
    ) -> Optional[RssFeed]:
        feed = await self.get_by_id(feed_id)
        if not feed:
            return None
        now = datetime.now(timezone.utc)
        if success:
            feed.last_success_at = now
            feed.failure_count = 0
            feed.last_error = None
        else:
            feed.last_failure_at = now
            feed.failure_count = (feed.failure_count or 0) + 1
            feed.last_error = error
        await self.session.commit()
        await self.session.refresh(feed)
        return feed
