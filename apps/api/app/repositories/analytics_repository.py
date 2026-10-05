from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import PublicationMetricsSnapshot
from app.models.content_family import ContentItem
from app.models.script import ScriptDraft
from app.engines.analytics.analyzer import AnalyticsAnalyzer
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[PublicationMetricsSnapshot]):
    """Storage boundary for platform metrics, performance signals, hook rankings, and creator ROI."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.analyzer = AnalyticsAnalyzer()

    async def record_snapshot(self, data: Dict[str, Any]) -> PublicationMetricsSnapshot:
        """Persists a new publication performance snapshot."""
        snapshot = PublicationMetricsSnapshot(
            content_item_id=data["content_item_id"],
            platform_publication_id=data.get("platform_publication_id"),
            platform=data.get("platform", "youtube").lower(),
            snapshot_timestamp=data.get("snapshot_timestamp") or datetime.now(timezone.utc),
            snapshot_label=data.get("snapshot_label", "24h"),
            views=int(data.get("views", 0)),
            impressions=int(data.get("impressions", 0)),
            watch_time_seconds=float(data.get("watch_time_seconds", 0.0)),
            average_view_duration_seconds=float(data.get("average_view_duration_seconds", 0.0)),
            retention_rate_pct=float(data.get("retention_rate_pct", 0.0)),
            hook_retention_3s_pct=float(data["hook_retention_3s_pct"]) if data.get("hook_retention_3s_pct") is not None else None,
            hook_retention_30s_pct=float(data["hook_retention_30s_pct"]) if data.get("hook_retention_30s_pct") is not None else None,
            likes=int(data.get("likes", 0)),
            comments=int(data.get("comments", 0)),
            shares=int(data.get("shares", 0)),
            saves=int(data.get("saves", 0)),
            clicks=int(data.get("clicks", 0)),
            subscribers_gained=int(data.get("subscribers_gained", 0)),
            revenue_estimated_usd=float(data.get("revenue_estimated_usd", 0.0)),
            notes=data.get("notes"),
            source=data.get("source", "MANUAL"),
            raw_metadata=data.get("raw_metadata", {}),
        )
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[PublicationMetricsSnapshot]:
        """Fetches a single snapshot by ID."""
        stmt = select(PublicationMetricsSnapshot).where(PublicationMetricsSnapshot.id == snapshot_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        """Deletes a snapshot record."""
        snapshot = await self.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        await self.session.delete(snapshot)
        await self.session.commit()
        return True

    async def list_snapshots(
        self,
        content_item_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[PublicationMetricsSnapshot]:
        """Lists snapshots with optional filtering."""
        stmt = select(PublicationMetricsSnapshot)
        if content_item_id:
            stmt = stmt.where(PublicationMetricsSnapshot.content_item_id == content_item_id)
        if platform:
            stmt = stmt.where(PublicationMetricsSnapshot.platform == platform.lower())
        stmt = stmt.order_by(PublicationMetricsSnapshot.snapshot_timestamp.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_snapshots_by_item(self, content_item_id: str) -> List[PublicationMetricsSnapshot]:
        """Retrieves all snapshots for a given content item chronologically."""
        stmt = (
            select(PublicationMetricsSnapshot)
            .where(PublicationMetricsSnapshot.content_item_id == content_item_id)
            .order_by(PublicationMetricsSnapshot.snapshot_timestamp.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Generates studio-wide creator performance summary dashboard."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get snapshots within date range (or all if empty)
        stmt = (
            select(PublicationMetricsSnapshot)
            .where(PublicationMetricsSnapshot.snapshot_timestamp >= cutoff)
            .order_by(PublicationMetricsSnapshot.snapshot_timestamp.desc())
        )
        res = await self.session.execute(stmt)
        snapshots = list(res.scalars().all())

        if not snapshots:
            # Fallback to all snapshots
            res_all = await self.session.execute(select(PublicationMetricsSnapshot).order_by(PublicationMetricsSnapshot.snapshot_timestamp.desc()))
            snapshots = list(res_all.scalars().all())

        total_views = sum(s.views for s in snapshots)
        total_impressions = sum(s.impressions for s in snapshots)
        total_watch_seconds = sum(s.watch_time_seconds for s in snapshots)
        total_likes = sum(s.likes for s in snapshots)
        total_comments = sum(s.comments for s in snapshots)
        total_shares = sum(s.shares for s in snapshots)
        total_saves = sum(s.saves for s in snapshots)
        total_revenue = sum(s.revenue_estimated_usd for s in snapshots)

        total_engagements = total_likes + total_comments + total_shares + total_saves
        overall_engagement_rate = round((total_engagements / max(total_views, 1)) * 100.0, 2)

        hook_retentions = [s.hook_retention_3s_pct for s in snapshots if s.hook_retention_3s_pct is not None]
        avg_3s_hook = round(sum(hook_retentions) / max(len(hook_retentions), 1), 1) if hook_retentions else 0.0

        unique_items = len(set(s.content_item_id for s in snapshots))

        # Platform aggregation
        snapshot_dicts = [
            {
                "platform": s.platform,
                "views": s.views,
                "likes": s.likes,
                "comments": s.comments,
                "shares": s.shares,
                "saves": s.saves,
                "revenue_estimated_usd": s.revenue_estimated_usd,
                "retention_rate_pct": s.retention_rate_pct,
            }
            for s in snapshots
        ]
        platform_breakdowns = self.analyzer.aggregate_platforms(snapshot_dicts)

        # Top hooks
        top_hooks = await self.get_hook_rankings(limit=5)

        # Economics
        production_cost = round(unique_items * (0.05 + (45.0 / 60.0) * 50.0), 2)
        roi_multiplier = round(total_revenue / max(production_cost, 0.01), 2)

        return {
            "days": days,
            "total_snapshots": len(snapshots),
            "total_published_items": unique_items,
            "total_views": total_views,
            "total_impressions": total_impressions,
            "total_watch_time_hours": round(total_watch_seconds / 3600.0, 2),
            "total_engagements": total_engagements,
            "overall_engagement_rate_pct": overall_engagement_rate,
            "avg_3s_hook_retention_pct": avg_3s_hook,
            "total_revenue_usd": round(total_revenue, 2),
            "total_production_cost_usd": production_cost,
            "overall_roi_multiplier": roi_multiplier,
            "platforms": [p.model_dump() for p in platform_breakdowns],
            "top_hooks": top_hooks,
            "recent_snapshots": [
                {
                    "id": s.id,
                    "content_item_id": s.content_item_id,
                    "platform_publication_id": s.platform_publication_id,
                    "platform": s.platform,
                    "snapshot_label": s.snapshot_label,
                    "snapshot_timestamp": s.snapshot_timestamp,
                    "views": s.views,
                    "impressions": s.impressions,
                    "watch_time_seconds": s.watch_time_seconds,
                    "average_view_duration_seconds": s.average_view_duration_seconds,
                    "retention_rate_pct": s.retention_rate_pct,
                    "hook_retention_3s_pct": s.hook_retention_3s_pct,
                    "hook_retention_30s_pct": s.hook_retention_30s_pct,
                    "likes": s.likes,
                    "comments": s.comments,
                    "shares": s.shares,
                    "saves": s.saves,
                    "clicks": s.clicks,
                    "subscribers_gained": s.subscribers_gained,
                    "revenue_estimated_usd": s.revenue_estimated_usd,
                    "engagement_rate_pct": self.analyzer.calculate_engagement_rate(s.views, s.likes, s.comments, s.shares, s.saves),
                    "notes": s.notes,
                    "source": s.source,
                    "raw_metadata": s.raw_metadata or {},
                    "created_at": s.created_at,
                }
                for s in snapshots[:15]
            ],
        }

    async def get_hook_rankings(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieves and evaluates hook retention records paired with script opening lines."""
        stmt = (
            select(PublicationMetricsSnapshot)
            .where(PublicationMetricsSnapshot.hook_retention_3s_pct.is_not(None))
            .order_by(PublicationMetricsSnapshot.hook_retention_3s_pct.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        snapshots = list(res.scalars().all())

        results = []
        for s in snapshots:
            # Query item title and script hook
            item_stmt = select(ContentItem).where(ContentItem.id == s.content_item_id)
            item_res = await self.session.execute(item_stmt)
            item = item_res.scalars().first()
            title = item.working_title if item else "Unknown Content Item"

            script_stmt = (
                select(ScriptDraft)
                .where(ScriptDraft.content_item_id == s.content_item_id)
                .options(selectinload(ScriptDraft.sections))
                .order_by(ScriptDraft.created_at.desc())
            )
            script_res = await self.session.execute(script_stmt)
            script = script_res.scalars().first()
            hook_text = ""
            if script:
                if script.sections:
                    hook_sec = next((sec for sec in script.sections if sec.section_type == "hook"), None)
                    if hook_sec and hook_sec.narration:
                        hook_text = hook_sec.narration
                    elif script.sections[0].narration:
                        hook_text = script.sections[0].narration
                if not hook_text:
                    hook_text = script.title

            insight = self.analyzer.evaluate_hook(
                content_item_id=s.content_item_id,
                content_title=title,
                hook_text=hook_text,
                platform=s.platform,
                views=s.views,
                hook_retention_3s_pct=s.hook_retention_3s_pct or 0.0,
                hook_retention_30s_pct=s.hook_retention_30s_pct,
            )
            results.append(insight.model_dump())

        return results

    async def get_item_roi(self, content_item_id: str) -> Dict[str, Any]:
        """Calculates detailed content return on investment for a single content item."""
        item_stmt = select(ContentItem).where(ContentItem.id == content_item_id)
        item_res = await self.session.execute(item_stmt)
        item = item_res.scalars().first()
        title = item.working_title if item else "Unknown Content"

        snapshots = await self.get_snapshots_by_item(content_item_id)
        total_views = sum(s.views for s in snapshots)
        total_revenue = sum(s.revenue_estimated_usd for s in snapshots)

        # AI cost estimation
        ai_cost = 0.04
        roi_analysis = self.analyzer.calculate_roi(
            content_item_id=content_item_id,
            content_title=title,
            total_views=total_views,
            total_revenue_usd=total_revenue,
            ai_cost_usd=ai_cost,
        )
        return roi_analysis.model_dump()
