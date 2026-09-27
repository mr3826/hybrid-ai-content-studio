from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.export import ExportPackage
from app.repositories.base import BaseRepository


class ExportRepository(BaseRepository[ExportPackage]):
    """Data access repository for ExportPackage domain entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, package: ExportPackage) -> ExportPackage:
        self.session.add(package)
        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def get_by_id(self, package_id: str) -> Optional[ExportPackage]:
        stmt = (
            select(ExportPackage)
            .where(ExportPackage.id == package_id)
            .options(selectinload(ExportPackage.publications))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_latest_for_item(self, item_id: str) -> Optional[ExportPackage]:
        stmt = (
            select(ExportPackage)
            .where(ExportPackage.content_item_id == item_id)
            .options(selectinload(ExportPackage.publications))
            .order_by(desc(ExportPackage.created_at))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_item(self, item_id: str) -> List[ExportPackage]:
        stmt = (
            select(ExportPackage)
            .where(ExportPackage.content_item_id == item_id)
            .order_by(desc(ExportPackage.created_at))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_all(self, limit: int = 50) -> List[ExportPackage]:
        stmt = (
            select(ExportPackage)
            .order_by(desc(ExportPackage.created_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
