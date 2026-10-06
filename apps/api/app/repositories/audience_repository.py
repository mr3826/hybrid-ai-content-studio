import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audience import LeadMagnet, AudienceConversion
from app.repositories.base import BaseRepository


class AudienceRepository(BaseRepository[LeadMagnet]):
    """Storage repository boundary for owned audience lead magnets and conversion attribution snapshots."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_lead_magnet(self, data: Dict[str, Any]) -> LeadMagnet:
        """Create and persist a new lead magnet asset."""
        magnet = LeadMagnet(
            id=data.get("id") or str(uuid.uuid4()),
            title=data["title"],
            slug=data["slug"],
            description=data["description"],
            magnet_type=data.get("magnet_type", "cheat_sheet"),
            landing_page_url=data["landing_page_url"],
            cta_copy=data["cta_copy"],
            status=data.get("status", "ACTIVE"),
            target_pillar=data.get("target_pillar", "Core"),
            estimated_value_usd=data.get("estimated_value_usd", 15.0),
            total_downloads=data.get("total_downloads", 0),
        )
        self.session.add(magnet)
        await self.session.commit()
        await self.session.refresh(magnet)
        return magnet

    async def get_lead_magnet(self, magnet_id: str) -> Optional[LeadMagnet]:
        """Fetch single lead magnet by ID."""
        stmt = select(LeadMagnet).where(LeadMagnet.id == magnet_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_lead_magnet_by_slug(self, slug: str) -> Optional[LeadMagnet]:
        """Fetch lead magnet by unique slug."""
        stmt = select(LeadMagnet).where(LeadMagnet.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_lead_magnets(
        self,
        status: Optional[str] = None,
        magnet_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LeadMagnet]:
        """List lead magnets with optional filtering."""
        stmt = select(LeadMagnet)
        if status:
            stmt = stmt.where(LeadMagnet.status == status)
        if magnet_type:
            stmt = stmt.where(LeadMagnet.magnet_type == magnet_type)
        stmt = stmt.order_by(LeadMagnet.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_lead_magnet(self, magnet_id: str, data: Dict[str, Any]) -> Optional[LeadMagnet]:
        """Update lead magnet fields."""
        magnet = await self.get_lead_magnet(magnet_id)
        if not magnet:
            return None

        for field in ("title", "slug", "description", "magnet_type", "landing_page_url", "cta_copy", "status", "target_pillar", "estimated_value_usd", "total_downloads"):
            if field in data and data[field] is not None:
                setattr(magnet, field, data[field])

        await self.session.commit()
        await self.session.refresh(magnet)
        return magnet

    async def delete_lead_magnet(self, magnet_id: str) -> bool:
        """Delete lead magnet by ID."""
        magnet = await self.get_lead_magnet(magnet_id)
        if not magnet:
            return False
        await self.session.delete(magnet)
        await self.session.commit()
        return True

    async def record_conversion(self, data: Dict[str, Any]) -> AudienceConversion:
        """Record a conversion or traffic snapshot attributed to a lead magnet / content item."""
        conv = AudienceConversion(
            id=data.get("id") or str(uuid.uuid4()),
            lead_magnet_id=data.get("lead_magnet_id"),
            content_item_id=data.get("content_item_id"),
            platform=data["platform"],
            utm_source=data.get("utm_source"),
            utm_medium=data.get("utm_medium"),
            utm_campaign=data.get("utm_campaign"),
            conversion_timestamp=data.get("conversion_timestamp") or datetime.now(timezone.utc),
            clicks=data.get("clicks", 0),
            signups=data.get("signups", 0),
            customers=data.get("customers", 0),
            revenue_usd=data.get("revenue_usd", 0.0),
            notes=data.get("notes"),
            source=data.get("source", "MANUAL"),
        )
        self.session.add(conv)

        # Update total_downloads on parent lead_magnet if signups occurred
        if conv.lead_magnet_id and conv.signups > 0:
            parent = await self.get_lead_magnet(conv.lead_magnet_id)
            if parent:
                parent.total_downloads += conv.signups

        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get_conversion(self, conversion_id: str) -> Optional[AudienceConversion]:
        """Fetch single conversion by ID."""
        stmt = (
            select(AudienceConversion)
            .where(AudienceConversion.id == conversion_id)
            .options(
                selectinload(AudienceConversion.lead_magnet),
                selectinload(AudienceConversion.content_item),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_conversions(
        self,
        lead_magnet_id: Optional[str] = None,
        platform: Optional[str] = None,
        content_item_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AudienceConversion]:
        """List conversions with optional filtering."""
        stmt = (
            select(AudienceConversion)
            .options(
                selectinload(AudienceConversion.lead_magnet),
                selectinload(AudienceConversion.content_item),
            )
        )
        if lead_magnet_id:
            stmt = stmt.where(AudienceConversion.lead_magnet_id == lead_magnet_id)
        if platform:
            stmt = stmt.where(AudienceConversion.platform == platform)
        if content_item_id:
            stmt = stmt.where(AudienceConversion.content_item_id == content_item_id)

        stmt = stmt.order_by(AudienceConversion.conversion_timestamp.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_magnet_metrics(self, magnet_id: str) -> Dict[str, Any]:
        """Aggregate clicks, signups, customers, and revenue for a specific lead magnet."""
        stmt = (
            select(
                func.count(AudienceConversion.id).label("conversions_count"),
                func.coalesce(func.sum(AudienceConversion.clicks), 0).label("total_clicks"),
                func.coalesce(func.sum(AudienceConversion.signups), 0).label("total_signups"),
                func.coalesce(func.sum(AudienceConversion.customers), 0).label("total_customers"),
                func.coalesce(func.sum(AudienceConversion.revenue_usd), 0.0).label("total_revenue"),
            )
            .where(AudienceConversion.lead_magnet_id == magnet_id)
        )
        res = await self.session.execute(stmt)
        row = res.one()

        total_clicks = int(row.total_clicks)
        total_signups = int(row.total_signups)
        conv_rate = round((total_signups / total_clicks * 100), 2) if total_clicks > 0 else 0.0

        return {
            "conversions_count": int(row.conversions_count),
            "total_clicks": total_clicks,
            "total_signups": total_signups,
            "total_customers": int(row.total_customers),
            "total_revenue_usd": round(float(row.total_revenue), 2),
            "conversion_rate_pct": conv_rate,
        }

    async def get_audience_summary(self) -> Dict[str, Any]:
        """Aggregate studio-wide metrics across all lead magnets and conversions."""
        magnets = await self.list_lead_magnets(limit=1000)
        conversions = await self.list_conversions(limit=5000)

        magnets_data = [
            {
                "id": m.id,
                "title": m.title,
                "slug": m.slug,
                "magnet_type": m.magnet_type,
                "status": m.status,
                "estimated_value_usd": m.estimated_value_usd,
            }
            for m in magnets
        ]
        conversions_data = [
            {
                "id": c.id,
                "lead_magnet_id": c.lead_magnet_id,
                "platform": c.platform,
                "clicks": c.clicks,
                "signups": c.signups,
                "customers": c.customers,
                "revenue_usd": c.revenue_usd,
            }
            for c in conversions
        ]

        from app.engines.audience.analyzer import AudienceAnalyzer
        analyzer = AudienceAnalyzer(rules={})
        return analyzer.aggregate_summary(magnets=magnets_data, conversions=conversions_data)
