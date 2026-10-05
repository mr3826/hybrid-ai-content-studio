from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_rights import AssetRightsRecord, AssetRightsStatus
from app.repositories.base import BaseRepository


class AssetRightsRepository(BaseRepository[AssetRightsRecord]):
    """Data access repository for AssetRightsRecord entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(self, record: AssetRightsRecord) -> AssetRightsRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_id(self, record_id: str) -> Optional[AssetRightsRecord]:
        stmt = select(AssetRightsRecord).where(AssetRightsRecord.id == record_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def update(self, record: AssetRightsRecord) -> AssetRightsRecord:
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete(self, record_id: str) -> bool:
        record = await self.get_by_id(record_id)
        if not record:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def list_records(
        self,
        content_item_id: Optional[str] = None,
        status: Optional[str] = None,
        asset_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AssetRightsRecord]:
        stmt = select(AssetRightsRecord)
        if content_item_id:
            stmt = stmt.where(AssetRightsRecord.content_item_id == content_item_id)
        if status and status != "all":
            stmt = stmt.where(AssetRightsRecord.status == status)
        if asset_type and asset_type != "all":
            stmt = stmt.where(AssetRightsRecord.asset_type == asset_type)

        stmt = stmt.order_by(desc(AssetRightsRecord.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_summary(self) -> Dict[str, Any]:
        """Calculates global rights statistics."""
        stmt = select(
            AssetRightsRecord.status,
            func.count(AssetRightsRecord.id).label("count")
        ).group_by(AssetRightsRecord.status)
        res = await self.session.execute(stmt)
        counts = {row[0]: row[1] for row in res.all()}

        total = sum(counts.values())
        verified = counts.get(AssetRightsStatus.VERIFIED, 0)
        unknown = counts.get(AssetRightsStatus.UNKNOWN, 0)
        requires_attribution = counts.get(AssetRightsStatus.REQUIRES_ATTRIBUTION, 0)
        do_not_use = counts.get(AssetRightsStatus.DO_NOT_USE, 0)

        return {
            "total_assets": total,
            "verified": verified,
            "unknown": unknown,
            "requires_attribution": requires_attribution,
            "do_not_use": do_not_use,
            "safe_percentage": round((verified / total * 100) if total > 0 else 100, 1),
        }
